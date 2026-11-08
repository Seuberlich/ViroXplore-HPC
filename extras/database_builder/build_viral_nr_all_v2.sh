#!/usr/bin/env bash
#SBATCH --job-name=nr_viral_all
#SBATCH --partition=SET_YOUR_PARTITION
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=nr_viral_all.%j.out
#SBATCH --error=nr_viral_all.%j.err

# v2: TaxID map layout detection + preflight checks before costly scan.
# Build a PHYSICALLY SMALLER NCBI-nr-derived DIAMOND database containing ALL
# proteins assigned to NCBI Viruses (taxid 10239), INCLUDING bacteriophages and
# archaeal viruses. Filtering phages belongs in the downstream discovery step.
# Self-contained: NO external filter_viral_nr.py needed.
# Paths below are examples and must be edited for each cluster.
# Local DIAMOND must be available in the SLURM job environment.
set -Eeuo pipefail

# =============== EDIT THESE SETTINGS =======================================
NR_FASTA="${NR_FASTA:-/absolute/path/to/nr.faa}"  # nr.faa OR nr.faa.gz
ACC2TAXID="${ACC2TAXID:-/absolute/path/to/prot.accession2taxid.FULL.gz}" # FULL is preferable
TAXONOMY_DIR="${TAXONOMY_DIR:-/absolute/path/to/ncbi_taxonomy}" # nodes.dmp + names.dmp
OUTPUT_DIR="${OUTPUT_DIR:-/absolute/path/to/output_viral_db}" # must have free space
APPTAINER_SIF=""      # existing v6 .sif
DB_NAME="${DB_NAME:-viral_all_nr_20261007}"                            # output: DB_NAME.dmnd
# ============================================================================

THREADS="${SLURM_CPUS_PER_TASK:-8}"

say() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }
trap 'echo "ERROR: database build stopped at line $LINENO (exit status $?). Check SLURM logs." >&2' ERR

[[ -f "$NR_FASTA" && -s "$NR_FASTA" ]] || fail "Missing or empty FASTA: $NR_FASTA"
[[ -f "$ACC2TAXID" && -s "$ACC2TAXID" ]] || fail "Missing accession map: $ACC2TAXID"
[[ -s "$TAXONOMY_DIR/nodes.dmp" ]] || fail "Missing $TAXONOMY_DIR/nodes.dmp"
[[ -s "$TAXONOMY_DIR/names.dmp" ]] || fail "Missing $TAXONOMY_DIR/names.dmp"
[[ -n "$OUTPUT_DIR" && "$OUTPUT_DIR" != / ]] || fail 'Invalid OUTPUT_DIR'
[[ "$DB_NAME" =~ ^[a-zA-Z0-9_-]+$ ]] || fail 'DB_NAME must be alphanumeric, _ or -'
command -v python3 >/dev/null 2>&1 || fail 'python3 is required on the host'
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd -P)"
export NR_FASTA ACC2TAXID TAXONOMY_DIR OUTPUT_DIR DB_NAME

if [[ -n "$APPTAINER_SIF" ]]; then
    [[ -s "$APPTAINER_SIF" ]] || fail "Missing .sif: $APPTAINER_SIF"
    command -v apptainer >/dev/null 2>&1 || fail 'apptainer not available'
    # Explicit binds: HPC /data/project directories are not necessarily auto-mounted.
    diamond_cmd=(apptainer exec
      --bind "$(dirname "$NR_FASTA"):$(dirname "$NR_FASTA")"
      --bind "$(dirname "$ACC2TAXID"):$(dirname "$ACC2TAXID")"
      --bind "$TAXONOMY_DIR:$TAXONOMY_DIR"
      --bind "$OUTPUT_DIR:$OUTPUT_DIR"
      "$APPTAINER_SIF" diamond)
else
    command -v diamond >/dev/null 2>&1 || fail 'diamond unavailable (or set APPTAINER_SIF)'
    diamond_cmd=(diamond)
fi

say 'Build configuration:'
printf '  FASTA:      %s\n  Taxon map:  %s\n  Taxonomy:   %s\n  Output:     %s\n  DB name:    %s\n  Threads:    %s\n' \
       "$NR_FASTA" "$ACC2TAXID" "$TAXONOMY_DIR" "$OUTPUT_DIR" "$DB_NAME" "$THREADS"
"${diamond_cmd[@]}" version

# We never delete or change the original nr.faa / FULL / taxonomy inputs.
# The .filter_complete marker allows restarting a failed DIAMOND makedb without
# repeating the expensive 20+ GB gzipped accession-map scan.
FILTER_COMPLETE="$OUTPUT_DIR/.${DB_NAME}.filter_complete"
FASTA_OUT="$OUTPUT_DIR/$DB_NAME.faa"
TAXMAP_OUT="$OUTPUT_DIR/$DB_NAME.accession2taxid.tsv.gz"
SUMMARY_OUT="$OUTPUT_DIR/$DB_NAME.filter_summary.json"

if [[ -s "$FILTER_COMPLETE" && -s "$FASTA_OUT" && -s "$TAXMAP_OUT" && -s "$SUMMARY_OUT" ]]; then
    say 'Completed filtered FASTA and taxon map already exist; skipping extraction.'
    say 'To rebuild from new inputs, use a DIFFERENT OUTPUT_DIR (recommended).'
else
    if [[ -e "$FASTA_OUT" || -e "$TAXMAP_OUT" || -e "$FILTER_COMPLETE" ]]; then
        fail "Incomplete or old outputs found in $OUTPUT_DIR. Use a NEW OUTPUT_DIR; do not mix builds."
    fi
    say 'Extracting ALL viral nr protein sequences, including phages and archaeal viruses.'
    python3 - <<'PY'
import gzip
import json
import os
import re
import sys
import time
from pathlib import Path

nr = Path(os.environ['NR_FASTA'])
accession_map = Path(os.environ['ACC2TAXID'])
tax_dir = Path(os.environ['TAXONOMY_DIR'])
out = Path(os.environ['OUTPUT_DIR'])
name = os.environ['DB_NAME']
fa_path = out / (name + '.faa')
map_path = out / (name + '.accession2taxid.tsv.gz')
summary_path = out / (name + '.filter_summary.json')
marker_path = out / ('.' + name + '.filter_complete')

def log(msg):
    print(time.strftime('[%Y-%m-%d %H:%M:%S]'), msg, flush=True)

def open_binary(p):
    return gzip.open(p, 'rb') if str(p).lower().endswith('.gz') else open(p, 'rb', buffering=1024*1024)

log('Loading NCBI taxonomy parent relationships ...')
parent = {}
with open(tax_dir / 'nodes.dmp', encoding='utf-8') as stream:
    for line in stream:
        p = line.split('|')
        if len(p) >= 2:
            parent[int(p[0].strip())] = int(p[1].strip())
if 10239 not in parent or 1 not in parent:
    raise RuntimeError('nodes.dmp is missing NCBI Viruses (10239) or root (1)')

# Classification exclusively by ancestry below root 10239.
# NO host inference and NO name/Division-based exclusions.
# Both bacteriophages and archaeal viruses are retained.
status = {1: False, 10239: True}
def is_virus(t):
    if t in status:
        return status[t]
    stack, seen = [], set()
    cur = t
    while cur not in status:
        if cur in seen:
            status[cur] = False
            break
        seen.add(cur)
        stack.append(cur)
        nxt = parent.get(cur)
        if nxt is None or nxt == cur:
            status[cur] = False
            break
        cur = nxt
    verdict = status[cur]
    for n in reversed(stack):
        status[n] = verdict
    return verdict

viral_taxids = {tax for tax in parent if is_virus(tax)}
log(f'Viral TaxIDs (including phages/archaeal viruses): {len(viral_taxids):,}')

# Safe regression controls when those TaxIDs are present in the taxonomy dump.
# These tests are NOT required to identify virus hosts; they only catch a broken ancestry walk.
checks = {
    10239: True, 2: False, 2157: False, 2759: False,
    11084: True, 11021: True, 11128: True, 11320: True,
    11676: True, 12242: True, 2697049: True,
    10710: True,  # Enterobacteria phage lambda: deliberately INCLUDED
}
control_results = []
for tid, expected in checks.items():
    if tid not in parent:
        continue
    got = is_virus(tid)
    control_results.append({'taxid': tid, 'expected_viral': expected, 'observed_viral': got})
    if got != expected:
        raise RuntimeError(f'Taxonomy regression failure: taxid {tid} expected {expected}, got {got}')
log(f'Taxonomy regression controls passed ({len(control_results)})')

# Store only viral accession.version keys; the enormous nonviral accession2taxid
# rows are discarded immediately. RAM is bounded by the number of viral IDs,
# not by the size of the full nr accession mapping.
viral_ids = {}
stat = dict(taxonomy_nodes=len(parent), viral_taxids=len(viral_taxids),
            accession_rows_read=0, viral_accession_rows=0,
            viral_accessions_indexed=0, duplicate_viral_accessions=0,
            conflicting_viral_taxids=0, invalid_taxids=0, unknown_taxids=0,
            fasta_records_scanned=0, fasta_records_kept=0,
            fasta_records_no_viral_accession=0,
            mixed_origin_nr_records=0, mixed_viral_taxid_nr_records=0,
            aa_letters_kept=0, regression_controls=control_results)

log('Validating protein-to-taxonomy mapping format before full scan ...')
# NCBI may distribute accession2taxid tables with differing numbers of columns.
# The full mapping usually has accession, accession.version, taxid, gi, but a
# two-column accession.version/taxid mapping is also supported here.
def guess_layout(first_line):
    fields = first_line.rstrip(b'\r\n').split(b'\t')
    labels = [v.strip().lstrip(b'#').lower() for v in fields]
    if b'taxid' in labels:
        tid_col = labels.index(b'taxid')
        if b'accession.version' in labels:
            accession_col = labels.index(b'accession.version')
        elif b'accession' in labels:
            accession_col = labels.index(b'accession')
        else:
            raise RuntimeError(f'Accession column missing from taxon-map header: {labels!r}')
        return tid_col, accession_col, True
    # No header: infer based on common data layouts.
    if len(fields) >= 3 and fields[2].strip().isdigit():
        return 2, 1, False
    if len(fields) >= 2 and fields[1].strip().isdigit():
        return 1, 0, False
    raise RuntimeError(
        'Could not identify columns in accession2taxid file. '
        f'First line contains {len(fields)} tab-delimited columns: '
        f'{[x[:60].decode("ascii", "replace") for x in fields[:5]]!r}. '
        'File may have an unexpected format or be corrupted.'
    )

with open_binary(accession_map) as fh:
    first_line = fh.readline()
    if not first_line:
        raise RuntimeError('Accession-to-taxid file is empty')
    taxid_col, acc_col, has_header = guess_layout(first_line)
    log(f'Taxmap detected: {len(first_line.split(bytes([9])))} columns in first row; '
        f'accession.version column {acc_col + 1}, TaxID column {taxid_col + 1}, '
        f'header={has_header}')
    log('First row (truncated): ' + repr(first_line[:180].decode('ascii', 'replace').strip()))

# Quick preflight of taxid parsing and consistency; this prevents hours wasted
# scanning a 26-GB mapping file in an unrecognized format.
preflight_lines = 100000
check_total = valid_numeric = known_taxids = 0
with open_binary(accession_map) as fh:
    if has_header:
        fh.readline()
    for line in fh:
        if check_total >= preflight_lines:
            break
        check_total += 1
        fields = line.rstrip(b'\r\n').split(b'\t')
        if len(fields) <= max(taxid_col, acc_col):
            continue
        try:
            tid = int(fields[taxid_col])
        except ValueError:
            continue
        valid_numeric += 1
        if tid in parent:
            known_taxids += 1
log(f'Taxmap preflight: {check_total:,} rows; numeric TaxIDs {valid_numeric:,}; '
    f'TaxIDs found in nodes.dmp {known_taxids:,}')
if check_total == 0 or valid_numeric < max(1, check_total // 2):
    raise RuntimeError('Taxmap preflight failed: unable to read numeric TaxIDs from selected column. '
                       'Check actual first lines of prot.accession2taxid.FULL.gz.')
if known_taxids < max(1, valid_numeric // 2):
    raise RuntimeError('Taxmap preflight failed: most TaxIDs are absent from nodes.dmp. '
                       'Check that accession2taxid and taxdump are compatible.')

log('Scanning NCBI prot.accession2taxid (can be many hours for FULL.gz) ...')
with open_binary(accession_map) as stream:
    if has_header:
        stream.readline()
    for ln in stream:
        stat['accession_rows_read'] += 1
        fields = ln.rstrip(b'\r\n').split(b'\t')
        if len(fields) <= max(taxid_col, acc_col):
            stat['invalid_taxids'] += 1
            continue
        try:
            tid = int(fields[taxid_col])
        except ValueError:
            stat['invalid_taxids'] += 1
            continue
        if tid not in parent:
            stat['unknown_taxids'] += 1
            continue
        if tid not in viral_taxids:
            continue
        acc = fields[acc_col].strip()
        if not acc:
            continue
        stat['viral_accession_rows'] += 1
        old = viral_ids.get(acc)
        if old is None:
            viral_ids[acc] = tid
        else:
            stat['duplicate_viral_accessions'] += 1
            if old != tid:
                stat['conflicting_viral_taxids'] += 1
                viral_ids[acc] = min(old, tid)
        if stat['accession_rows_read'] % 50000000 == 0:
            log(f"Accessions scanned: {stat['accession_rows_read']:,}; viral IDs: {len(viral_ids):,}")
stat['viral_accessions_indexed'] = len(viral_ids)
log(f'Indexed {len(viral_ids):,} virus-associated accession.version IDs')
log(f"Index diagnostics: {stat['accession_rows_read']:,} rows, "
    f"{stat['invalid_taxids']:,} invalid TaxIDs, {stat['unknown_taxids']:,} TaxIDs not in taxonomy")
if not viral_ids:
    raise RuntimeError('No viral accessions indexed despite valid TaxIDs. '
                       'Please provide the first 5 rows of the accession2taxid map '
                       'and the taxmap preflight statistics from this log.')

# Headers in nr.faa can contain multiple equivalent protein identifiers separated
# by ASCII 1. We select a VIRAL accession and its description, even when the nr
# representative's first accession belongs to a bacterium.
def from_header_segment(seg):
    seg = seg.strip()
    if not seg:
        return None, b''
    parts = seg.split(None, 1)
    token = parts[0]
    if b'|' in token:
        ps = token.split(b'|')
        if ps[0] == b'gi' and len(ps) >= 4:
            token = ps[3]
        elif ps[0] in (b'ref', b'gb', b'emb', b'dbj', b'sp', b'tr') and len(ps) >= 2:
            token = ps[1]
    return token, parts[1] if len(parts) > 1 else b''

log('Streaming nr FASTA; selecting viral records (including ALL phages) ...')
keep = False
with open_binary(nr) as stream, open(fa_path, 'wb', buffering=1024*1024) as fa, \
        gzip.open(map_path, 'wt', encoding='utf-8', compresslevel=4) as tm:
    tm.write('accession\taccession.version\ttaxid\tgi\n')
    for ln in stream:
        if ln.startswith(b'>'):
            stat['fasta_records_scanned'] += 1
            keep = False
            segments = ln[1:].rstrip(b'\r\n').split(b'\x01')
            valid = []
            for seg in segments:
                acc, description = from_header_segment(seg)
                if not acc:
                    continue
                tid = viral_ids.get(acc)
                if tid is not None:
                    valid.append((acc, tid, description))
            if valid:
                # Keep one sequence per nr record, choosing the first *viral* ID.
                acc, tid, desc = valid[0]
                if len(valid) < len(segments):
                    stat['mixed_origin_nr_records'] += 1
                if len({t for _, t, _ in valid}) > 1:
                    stat['mixed_viral_taxid_nr_records'] += 1
                fa.write(b'>' + acc + (b' ' + desc if desc else b'') + b'\n')
                tm.write(f'{acc.split(b".", 1)[0].decode("ascii", "replace")}\t{acc.decode("ascii", "replace")}\t{tid}\t0\n')
                stat['fasta_records_kept'] += 1
                keep = True
            else:
                stat['fasta_records_no_viral_accession'] += 1
            if stat['fasta_records_scanned'] % 5000000 == 0:
                log(f"nr records: {stat['fasta_records_scanned']:,}; viral retained: {stat['fasta_records_kept']:,}")
        elif keep:
            fa.write(ln)
            stat['aa_letters_kept'] += len(ln.strip())

if not stat['fasta_records_kept']:
    raise RuntimeError('No viral FASTA records retained; verify nr FASTA and accession-map releases')

# Guard against an accidentally almost-empty database on a gigantic nr input.
if stat['fasta_records_scanned'] > 1000000 and stat['fasta_records_kept'] < 1000:
    raise RuntimeError('Very few viral entries selected from a large nr input. Check accession matching!')

with open(summary_path, 'w', encoding='utf-8') as stream:
    json.dump(stat, stream, indent=2, sort_keys=True)
    stream.write('\n')
with open(marker_path, 'w', encoding='utf-8') as stream:
    stream.write('FASTA and accession2taxid extraction complete\n')
log('Extraction finished. Key statistics:')
for k in ('accession_rows_read', 'viral_accession_rows', 'viral_accessions_indexed',
          'fasta_records_scanned', 'fasta_records_kept', 'mixed_origin_nr_records',
          'aa_letters_kept'):
    log(f'  {k} = {stat[k]:,}')
PY
fi

[[ -s "$FASTA_OUT" && -s "$TAXMAP_OUT" ]] || fail 'Filtered FASTA/taxon-map is absent or empty'
[[ -s "$FILTER_COMPLETE" ]] || fail 'Extraction not marked complete'

# The FASTA records and custom taxon map use the SAME exact accession.version
# tokens. By default, DIAMOND removes the terminal .version suffix from both
# inputs; e.g. XVM46135.1 and XVM46135.2 collide as XVM46135 and makedb
# aborts with "Duplicate keys". --no-parse-seqids retains exact tokens.
# Supported in DIAMOND >= 2.1.7; validated against documented CLI for 2.2.5.
say 'Building DIAMOND .dmnd with exact accession.version IDs (--no-parse-seqids).'
# Keep all makedb arguments on a single physical line to avoid shell
# continuation errors (e.g., '--threads: command not found').
"${diamond_cmd[@]}" makedb --in "$FASTA_OUT" --db "$OUTPUT_DIR/$DB_NAME" --taxonmap "$TAXMAP_OUT" --taxonnodes "$TAXONOMY_DIR/nodes.dmp" --taxonnames "$TAXONOMY_DIR/names.dmp" --no-parse-seqids --threads "$THREADS"

[[ -s "$OUTPUT_DIR/$DB_NAME.dmnd" ]] || fail 'DIAMOND did not produce a nonempty .dmnd file'
say "SUCCESS: $OUTPUT_DIR/$DB_NAME.dmnd"
say "Summary: $SUMMARY_OUT"
say 'Do NOT apply --taxonlist 10239 unnecessarily to this viral-only database.'
