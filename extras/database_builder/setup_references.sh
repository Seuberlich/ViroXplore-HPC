#!/usr/bin/env bash
# ViroXplore-HPC: optional reference database downloader and builder.
# Run as an HPC batch job with network access and ample scratch storage.
# This utility is NOT launched by the five-stage discovery master.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
cat <<'HELP'
ViroXplore-HPC reference setup
Usage: bash setup_references.sh {refseq|nr|all|check|verify-offline} /absolute/reference/root

  refseq  Download NCBI RefSeq viral genomic FASTA, build Bowtie2 index,
          create DUST low-complexity BED and >=10-base homopolymer BED,
          and prepare offline accession/TaxID/organism metadata (GBFF).
  nr      Download complete NCBI nr BLAST database, reconstruct nr.faa,
          filter virus-taxonomy proteins (including phages) using the
          bundled builder, make DIAMOND .dmnd and validate it.
  all     Run refseq, then nr (very large disk/network requirements).
  check   Report available reference files and print pipeline paths.
  verify-offline  Validate RefSeq FASTA, Bowtie2 files and matching local
          SQLite metadata without downloading or altering data.

Requires: curl, python3, gzip, tar, sha256sum; BLAST+ (update_blastdb.pl,
blastdbcmd, dustmasker), Bowtie2 (bowtie2-build), DIAMOND 2.2.5+.
The BLAST nr and temporary nr.faa are deleted ONLY AFTER a verified .dmnd
was produced. Local user-supplied FASTA is NEVER removed.

Optional environment variables:
  THREADS=8
  NR_LOCAL_FASTA=/absolute/path/nr.faa  # avoid downloading the entire BLAST nr
  REMOVE_BLAST_SOURCE_AFTER_SUCCESS=1  # default 1, owned download only
  REMOVE_TEMP_NR_AFTER_SUCCESS=1       # default 1, owned FASTA only
  CONTAMINATION_TAXIDS_FILE=/absolute/path/curated_taxid_list
  REFSEQ_RELEASE_URL=https://ftp.ncbi.nlm.nih.gov/refseq/release/viral/
  REFSEQ_FILE_URLS_LIST=/absolute/path/refseq_urls.txt  # optional pinned URL list
HELP
}
case "${1:-}" in
 --help|-h) usage; exit 0 ;;
 refseq|nr|all|check|verify-offline) TASK="$1" ;;
 *) usage; exit 2 ;;
esac
ROOT="${2:-${REFERENCE_ROOT:-}}"
[[ "$ROOT" == /* && "$ROOT" != / && "$ROOT" != */.. && "$ROOT" != */. ]] || {
 echo "ERROR: provide an absolute, non-root reference directory" >&2; exit 2;
}
THREADS="${THREADS:-${SLURM_CPUS_PER_TASK:-8}}"
[[ "$THREADS" =~ ^[1-9][0-9]*$ ]] || { echo 'ERROR: THREADS must be positive' >&2; exit 2; }
log() { printf '[%s] ViroXplore-HPC reference setup: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "Required executable missing: $1 (load its HPC module)"; }
mkdir -p "$ROOT"
ROOT="$(cd "$ROOT" && pwd -P)"
[[ "$ROOT" != / ]] || fail 'Refusing the root directory'
TAXDIR="$ROOT/ncbi_taxonomy"
MAP="$ROOT/taxonomy_inputs/prot.accession2taxid.FULL.gz"
NRDIR="$ROOT/viral_nr"
NRFASTA="$ROOT/nr_build_tmp/nr.faa"
BLASTDIR="$ROOT/nr_build_tmp/blast_nr"
REFDIR="$ROOT/refseq_viral"
REF_FNA="$REFDIR/refseq_viral.fna"
REF_URL="${REFSEQ_RELEASE_URL:-https://ftp.ncbi.nlm.nih.gov/refseq/release/viral/}"

# Download to a .part file to distinguish partial/incomplete downloads.
# gzip validation is explicit at use-time. HTTP errors abort the setup.
download() {
 local url="$1" dest="$2" part="${2}.part"
 if [[ -s "$dest" ]]; then log "Reusing file: $dest"; return; fi
 need curl
 mkdir -p "$(dirname "$dest")"
 log "Downloading: $url"
 curl --fail --location --retry 6 --retry-delay 15 --continue-at - --output "$part" "$url"
 [[ -s "$part" ]] || fail "Empty download: $url"
 mv -- "$part" "$dest"
}

require_taxonomy() {
 need tar; need gzip; need python3
 mkdir -p "$TAXDIR" "$ROOT/taxonomy_inputs"
 local tarball="$ROOT/taxonomy_inputs/taxdump.tar.gz"
 download 'https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz' "$tarball"
 gzip -t "$tarball" || fail 'Taxonomy archive is corrupt'
 if [[ ! -s "$TAXDIR/nodes.dmp" || ! -s "$TAXDIR/names.dmp" ]]; then
   tar -xzf "$tarball" -C "$TAXDIR" nodes.dmp names.dmp
 fi
 [[ -s "$TAXDIR/nodes.dmp" && -s "$TAXDIR/names.dmp" ]] || fail 'Taxonomy extraction failed'
}

valid_nr() {
 need diamond
 local db="$NRDIR/viral_all_nr.dmnd"
 [[ -s "$db" ]] || return 1
 local info
 info="$(diamond dbinfo --db "$db" 2>&1)" || return 1
 printf '%s\n' "$info" | grep -Eq 'Sequences[[:space:]]+[1-9][0-9]*' || return 1
 printf '%s\n' "$info"
}

build_nr() {
 need python3; need gzip; need sha256sum; need blastdbcmd; need update_blastdb.pl; need diamond
 if [[ -s "$NRDIR/.nr_setup.complete" ]] && valid_nr >/dev/null; then
   log 'Completed viral DIAMOND database found; no new download required.'
   return 0
 fi
 log 'Preparing the complete NCBI nr source for taxonomic filtering.'
 require_taxonomy
 download 'https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/accession2taxid/prot.accession2taxid.FULL.gz' "$MAP"
 gzip -t "$MAP" || fail 'Protein accession-to-taxid mapping is corrupted'
 mkdir -p "$NRDIR" "$ROOT/nr_build_tmp"
 local original_user_fasta=0 input_fasta="$NRFASTA"
 if [[ -n "${NR_LOCAL_FASTA:-}" ]]; then
   input_fasta="$NR_LOCAL_FASTA"
   [[ "$input_fasta" == /* && -s "$input_fasta" ]] || fail 'NR_LOCAL_FASTA must be an existing absolute file'
   original_user_fasta=1
   log 'Using external nr FASTA; this file will never be deleted.'
 else
   # NCBI no longer distributes nr.gz as a FASTA download. Use the NCBI
   # formatted BLAST nr + blastdbcmd to regenerate the complete nr.faa.
   if [[ ! -s "$NRFASTA" ]]; then
     need update_blastdb.pl
     mkdir -p "$BLASTDIR"
     # Ownership marker prevents deleting a pre-existing BLAST database.
     if [[ ! -f "$BLASTDIR/.viroxplore_owned" ]]; then
       if [[ -n "$(find "$BLASTDIR" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
         fail 'BLAST source directory already has data without ownership marker; refuse to modify it'
       fi
       printf 'Created by ViroXplore-HPC reference setup\n' > "$BLASTDIR/.viroxplore_owned"
     fi
     log 'Downloading and decompressing full nr BLAST volumes (may require hundreds of GB).'
     (cd "$BLASTDIR" && update_blastdb.pl --decompress nr)
     log 'Reconstructing the COMPLETE nr.faa from BLAST volumes.'
     # Write to a temporary location until blastdbcmd exits successfully.
     rm -f -- "$NRFASTA.part"
     blastdbcmd -db "$BLASTDIR/nr" -entry all -out "$NRFASTA.part"
     [[ -s "$NRFASTA.part" ]] || fail 'blastdbcmd produced an empty FASTA'
     [[ "$(head -c 1 "$NRFASTA.part")" == '>' ]] || fail 'Unexpected FASTA content'
     mv -- "$NRFASTA.part" "$NRFASTA"
   else
     log "Reusing previously generated FASTA: $NRFASTA"
   fi
 fi
 log 'Building physically reduced viral nr DIAMOND database from complete nr FASTA.'
 NR_FASTA="$input_fasta" ACC2TAXID="$MAP" TAXONOMY_DIR="$TAXDIR" \
 OUTPUT_DIR="$NRDIR" DB_NAME='viral_all_nr' APPTAINER_SIF='' \
 SLURM_CPUS_PER_TASK="$THREADS" bash "$SCRIPT_DIR/build_viral_nr_all_v2.sh"
 valid_nr > "$NRDIR/diamond_dbinfo.txt" || fail 'DIAMOND database failed dbinfo or sequence-count verification; keeping all source data'
 [[ -s "$NRDIR/viral_all_nr.filter_summary.json" ]] || fail 'Builder summary absent; keeping source data'
 local sequence_count expected_count
 sequence_count="$(awk '$1=="Sequences" {print $2}' "$NRDIR/diamond_dbinfo.txt" | head -n 1)"
 expected_count="$(python3 - "$NRDIR/viral_all_nr.filter_summary.json" <<'PYCOUNT'
import json
import sys
with open(sys.argv[1]) as f:
    print(json.load(f).get('fasta_records_kept', 0))
PYCOUNT
)"
 [[ "$sequence_count" =~ ^[1-9][0-9]*$ && "$expected_count" == "$sequence_count" ]] || \
   fail "DIAMOND sequence count ($sequence_count) disagrees with extraction summary ($expected_count); keeping all source data"

 need date
 {
   echo "created_utc=$(date -u +%FT%TZ)"
   echo "input_fasta=$input_fasta"
   echo "taxdump_source=https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz"
   echo "taxmap_source=https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/accession2taxid/prot.accession2taxid.FULL.gz"
   diamond version
   sha256sum "$NRDIR/viral_all_nr.dmnd"
 } > "$NRDIR/build_manifest.txt"
 printf 'DIAMOND database validated; safe intermediate cleanup enabled\n' > "$NRDIR/.nr_setup.complete"
 log 'DIAMOND database validated; beginning optional cleanup.'
 if [[ "$original_user_fasta" -eq 0 && "${REMOVE_TEMP_NR_AFTER_SUCCESS:-1}" == 1 ]]; then
   [[ "$NRFASTA" == "$ROOT/nr_build_tmp/nr.faa" && ! -L "$NRFASTA" ]] || fail 'Unsafe nr FASTA cleanup path'
   rm -f -- "$NRFASTA"
   log 'Removed generated full nr.faa; viral DIAMOND database retained.'
 fi
 if [[ "$original_user_fasta" -eq 0 && "${REMOVE_BLAST_SOURCE_AFTER_SUCCESS:-1}" == 1 ]]; then
   [[ "$BLASTDIR" == "$ROOT/nr_build_tmp/blast_nr" && ! -L "$BLASTDIR" && -f "$BLASTDIR/.viroxplore_owned" ]] || fail 'Unsafe BLAST cleanup path'
   rm -rf -- "$BLASTDIR"
   log 'Removed downloaded full nr BLAST volumes.'
 fi
 log "Completed viral DIAMOND: $NRDIR/viral_all_nr.dmnd"
}

valid_refseq() {
 local base="$REF_FNA" extension="" part
 [[ -s "$base" ]] || return 1
 if [[ -s "${base}.1.bt2" ]]; then extension='bt2';
 elif [[ -s "${base}.1.bt2l" ]]; then extension='bt2l';
 else return 1; fi
 for part in 1 2 3 4 rev.1 rev.2; do
   [[ -s "${base}.${part}.${extension}" ]] || return 1
 done
 [[ -f "${base}.masked.bed" && -f "${base}.10homopolymers.bed" ]] || return 1
 [[ -f "$REFDIR/contam_suppl_table_3.taxids.list" ]] || return 1
}

build_refseq() {
 need curl; need gzip; need python3; need bowtie2-build; need dustmasker; need sha256sum
 mkdir -p "$REFDIR/downloads"
 if [[ -s "$REFDIR/.refseq_setup.complete" ]] && valid_refseq; then
   log 'Completed RefSeq viral index and BED files found; nothing to rebuild.'
   return 0
 fi
 [[ ! -e "$REF_FNA" && ! -e "$REF_FNA.part" ]] || fail "Incomplete RefSeq output found; move aside or clean: $REF_FNA"
 local namesfile="$REFDIR/downloads/refseq_files.txt"
 if [[ -n "${REFSEQ_FILE_URLS_LIST:-}" ]]; then
   [[ -s "$REFSEQ_FILE_URLS_LIST" ]] || fail 'REFSEQ_FILE_URLS_LIST is empty or missing'
   cp -- "$REFSEQ_FILE_URLS_LIST" "${namesfile}.part"
 else
   python3 "$SCRIPT_DIR/discover_refseq_files.py" "$REF_URL" > "${namesfile}.part"
 fi
 [[ -s "${namesfile}.part" ]] || fail 'No RefSeq viral genomic FASTA files found'
 mv -- "${namesfile}.part" "$namesfile"
 local src filename n=0
 while IFS= read -r src; do
   [[ "$src" == "$REF_URL"* ]] || fail "Unexpected RefSeq source URL: $src"
   filename="${src##*/}"
   [[ "$filename" =~ ^viral\.[0-9]+(\.[0-9]+)?\.genomic\.fna\.gz$ ]] || fail "Unsafe RefSeq filename: $filename"
   download "$src" "$REFDIR/downloads/$filename"
   gzip -t "$REFDIR/downloads/$filename" || fail "Corrupt RefSeq FASTA: $filename"
   gzip -dc "$REFDIR/downloads/$filename" >> "$REF_FNA.part"
   n=$((n+1))
 done < "$namesfile"
 [[ "$n" -gt 0 && -s "$REF_FNA.part" ]] || fail 'Combined RefSeq FASTA empty'
 [[ "$(head -c 1 "$REF_FNA.part")" == '>' ]] || fail 'Combined FASTA has invalid leading character'
 mv -- "$REF_FNA.part" "$REF_FNA"
 log "Building Bowtie2 index from $n RefSeq viral genomic FASTA file(s)."
 bowtie2-build --threads "$THREADS" "$REF_FNA" "$REF_FNA"
 if [[ ! -s "${REF_FNA}.1.bt2" && ! -s "${REF_FNA}.1.bt2l" ]]; then
   fail 'Bowtie2 index missing'
 fi
 log 'Computing DUST low-complexity mask and homopolymer annotations.'
 dustmasker -in "$REF_FNA" -infmt fasta -outfmt fasta -out "${REF_FNA}.dust.fasta"
 python3 "$SCRIPT_DIR/make_refseq_beds.py" --input "$REF_FNA" \
   --masked "${REF_FNA}.dust.fasta" \
   --low-complexity-bed "${REF_FNA}.masked.bed" \
   --homopolymers-bed "${REF_FNA}.10homopolymers.bed"
 rm -f -- "${REF_FNA}.dust.fasta"
 # Optional curated control; an empty file means contamination labels are NOT applied.
 if [[ -n "${CONTAMINATION_TAXIDS_FILE:-}" ]]; then
   [[ -f "$CONTAMINATION_TAXIDS_FILE" ]] || fail 'Missing CONTAMINATION_TAXIDS_FILE'
   cp -- "$CONTAMINATION_TAXIDS_FILE" "$REFDIR/contam_suppl_table_3.taxids.list"
 else
   [[ -e "$REFDIR/contam_suppl_table_3.taxids.list" ]] || : > "$REFDIR/contam_suppl_table_3.taxids.list"
   log 'WARNING: contamination TaxID list is empty; curate it separately if required.'
 fi
 valid_refseq || fail 'Reference FASTA, index, mask or contamination file missing'
 {
   echo "created_utc=$(date -u +%FT%TZ)"
   echo "refseq_release_url=$REF_URL"
   cat "$namesfile"
   sha256sum "$REF_FNA"
 } > "$REFDIR/build_manifest.txt"
 printf 'Bowtie2 index and BED files created\n' > "$REFDIR/.refseq_setup.complete"
 log "Completed RefSeq reference: $REF_FNA"
}

ensure_refseq_offline_metadata() {
 local installer="$SCRIPT_DIR/setup_refseq_offline_metadata.sh"
 [[ -s "$installer" ]] || fail "Offline metadata installer not found: $installer"
 bash "$installer" "$ROOT" || fail "Offline RefSeq metadata installation failed"
}

check_refs() {
 if valid_refseq; then log "OK RefSeq: $REF_FNA"; else log 'INCOMPLETE RefSeq reference'; fi
 if [[ -s "$REFDIR/refseq_viral_metadata.sqlite" ]]; then
   log "OK RefSeq offline metadata: $REFDIR/refseq_viral_metadata.sqlite"
 else
   log 'MISSING RefSeq offline metadata (02b will fail): run refseq task or setup_refseq_offline_metadata.sh'
 fi
 if valid_nr >/dev/null; then log "OK DIAMOND: $NRDIR/viral_all_nr.dmnd"; else log 'INCOMPLETE viral DIAMOND'; fi
 log "Taxonomy: $TAXDIR"
 log "Central configurator: REFERENCE_ROOT=$ROOT"
}
case "$TASK" in
 refseq) build_refseq; ensure_refseq_offline_metadata ;;
 nr) build_nr ;;
 all) build_refseq; ensure_refseq_offline_metadata; build_nr ;;
 check) check_refs ;;
 verify-offline) need python3; python3 "$SCRIPT_DIR/verify_refseq_offline.py" "$ROOT" ;;
esac
