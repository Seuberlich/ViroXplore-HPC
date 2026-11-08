#!/usr/bin/env bash
# One-time preparatory download; analysis stage 02b has no internet access.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="${1:-${REFERENCE_ROOT:-}}"
[[ "$ROOT" == /* && "$ROOT" != / ]] || { echo 'Usage: setup_refseq_offline_metadata.sh /ABSOLUTE/REFERENCE_ROOT' >&2; exit 2; }
REFDIR="$ROOT/refseq_viral"
FASTA="$REFDIR/refseq_viral.fna"
LIST="$REFDIR/downloads/refseq_files.txt"
NODES="$ROOT/ncbi_taxonomy/nodes.dmp"
NAMES="$ROOT/ncbi_taxonomy/names.dmp"
TAXDUMP="$ROOT/taxonomy_inputs/taxdump.tar.gz"
DB="$REFDIR/refseq_viral_metadata.sqlite"
PYTHON="${PYTHON:-python3}"
for f in "$FASTA" "$LIST"; do
  [[ -s "$f" ]] || { echo "ERROR: missing $f (run setup_references.sh refseq first)" >&2; exit 1; }
done
mkdir -p "$ROOT/ncbi_taxonomy" "$ROOT/taxonomy_inputs" "$REFDIR/downloads"

# Taxdump download is a SETUP operation only; analysis never calls the network.
if [[ ! -s "$NODES" || ! -s "$NAMES" ]]; then
  if [[ ! -s "$TAXDUMP" ]]; then
    echo 'Downloading NCBI taxonomy snapshot for offline setup'
    curl --fail --location --retry 6 --retry-delay 15 --continue-at - \
      --output "$TAXDUMP.part" 'https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz'
    mv -- "$TAXDUMP.part" "$TAXDUMP"
  fi
  gzip -t "$TAXDUMP"
  tar -xzf "$TAXDUMP" -C "$ROOT/ncbi_taxonomy" nodes.dmp names.dmp
fi
for f in "$NODES" "$NAMES"; do
  [[ -s "$f" ]] || { echo "ERROR: missing taxonomy file: $f" >&2; exit 1; }
done

# NCBI viral release names are typically viral.1.1.genomic.fna.gz for FASTA
# but viral.1.genomic.gbff.gz for corresponding GenBank records.
declare -A gbff_urls=()
while IFS= read -r url; do
  [[ -n "$url" ]] || continue
  name="${url##*/}"
  if [[ ! "$name" =~ ^viral\.([0-9]+)(\.[0-9]+)?\.genomic\.fna\.gz$ ]]; then
    echo "ERROR: unexpected RefSeq FASTA archive name: $name" >&2; exit 1
  fi
  group="${BASH_REMATCH[1]}"
  gbff_name="viral.${group}.genomic.gbff.gz"
  gbff_urls["$gbff_name"]="${url%/*}/${gbff_name}"
done < "$LIST"
[[ "${#gbff_urls[@]}" -gt 0 ]] || { echo 'ERROR: no GBFF URLs derived from FASTA manifest' >&2; exit 1; }

if [[ -s "$DB" && "${FORCE_REBUILD_OFFLINE_METADATA:-0}" != 1 ]]; then
  echo "Existing offline metadata found: $DB"
  "$PYTHON" - "$DB" "$FASTA" <<'PYVERIFY'
import hashlib, sqlite3, sys
p = sys.argv[2]
dig = hashlib.sha256()
with open(p, 'rb') as f:
    for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
        dig.update(chunk)
with sqlite3.connect('file:{}?mode=ro'.format(sys.argv[1]), uri=True) as con:
    info = dict(con.execute('SELECT key, value FROM info'))
    if info.get('format_version') != '1' or info.get('reference_fasta_sha256') != dig.hexdigest():
        sys.exit('ERROR: existing metadata does not match indexed RefSeq FASTA; set FORCE_REBUILD_OFFLINE_METADATA=1 to rebuild')
print('PASS: existing offline metadata matches FASTA checksum')
PYVERIFY
  exit 0
fi

mapfile -t names_sorted < <(printf '%s\n' "${!gbff_urls[@]}" | LC_ALL=C sort -V)
gbff_paths=()
for name in "${names_sorted[@]}"; do
  dest="$REFDIR/downloads/$name"
  if [[ ! -s "$dest" ]]; then
    echo "Downloading RefSeq GenBank snapshot: ${gbff_urls[$name]}"
    curl --fail --location --retry 6 --retry-delay 15 --continue-at - \
      --output "${dest}.part" "${gbff_urls[$name]}"
    [[ -s "${dest}.part" ]] || { echo "ERROR: empty GBFF download: $name" >&2; exit 1; }
    mv -- "${dest}.part" "$dest"
  fi
  echo "Verifying compressed GBFF archive: $dest"
  gzip -t "$dest"
  gbff_paths+=("$dest")
done

echo 'Building COMPLETE offline accession + taxonomy database from matched RefSeq releases'
"$PYTHON" "$SCRIPT_DIR/../../tools/offline_ncbi_metadata.py" build \
  --reference-fasta "$FASTA" --gbff "${gbff_paths[@]}" \
  --nodes "$NODES" --names "$NAMES" --database "$DB"
echo 'PASS: full offline metadata database available for stage 02b'
