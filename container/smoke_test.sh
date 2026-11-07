#!/usr/bin/env bash
set -Eeuo pipefail
failed=0
for name in python3 fastqc fastp STAR spades.py seqkit bowtie2 bowtie2-build samtools bedtools diamond splitFileByColumn Rscript pigz blastdbcmd; do
  if command -v "$name" >/dev/null 2>&1; then
    printf 'OK       %s (%s)\n' "$name" "$(command -v "$name")"
  else
    printf 'MISSING  %s\n' "$name" >&2; failed=1
  fi
done
if command -v python3 >/dev/null 2>&1; then
  python3 -c 'import sqlite3; print("OK       Python sqlite3")' || failed=1
fi
if command -v Rscript >/dev/null 2>&1; then
  Rscript --vanilla -e 'library(readr); cat("OK       R readr\n")' || failed=1
fi
if [[ "$failed" != 0 ]]; then
  echo 'FAIL: required runtime tool unavailable' >&2; exit 1
fi
echo 'PASS: offline runtime smoke test. This is not a PE/SE scientific validation.'
