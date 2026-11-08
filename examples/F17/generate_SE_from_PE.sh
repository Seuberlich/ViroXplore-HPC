#!/usr/bin/env bash
# Make the exact historical F17 SE demonstration file by concatenating gzip members.
set -euo pipefail
r1="${1:-F17_RNA_1Mio_R1.fastq.gz}"
r2="${2:-F17_RNA_1Mio_R2.fastq.gz}"
out="${3:-F17_RNA_1Mio_SE.fastq.gz}"
[[ -s "$r1" && -s "$r2" ]] || { echo "ERROR: R1/R2 missing or empty" >&2; exit 1; }
[[ "$out" != "$r1" && "$out" != "$r2" ]] || { echo "ERROR: output cannot be an input" >&2; exit 1; }
gzip -t "$r1" "$r2"
cat -- "$r1" "$r2" > "$out"
gzip -t "$out"
echo "Created $out (R1 records followed by R2 records)"
