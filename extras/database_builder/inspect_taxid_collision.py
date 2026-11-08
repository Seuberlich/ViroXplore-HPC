#!/usr/bin/env python3
"""Inspect a reported DIAMOND duplicate key in the generated viral taxon map.

Usage: python3 inspect_taxid_collision.py /path/to/viral_all_nr.accession2taxid.tsv.gz XVM46135
Reads the compressed map once. Only prints matching rows (limits output to 20).
"""
import gzip
import sys

if len(sys.argv) != 3:
    sys.exit("Usage: inspect_taxid_collision.py MAP.tsv.gz ACCESSION_BASE")
path, target = sys.argv[1:]
found, shown = 0, 0
with gzip.open(path, 'rt', encoding='utf-8') as reader:
    header = next(reader).strip()
    if header != 'accession\taccession.version\ttaxid\tgi':
        sys.exit('Unexpected taxonmap header: ' + header)
    for row in reader:
        fields = row.rstrip('\n').split('\t')
        if len(fields) < 3:
            continue
        if fields[1] == target or fields[1].startswith(target + '.'):
            found += 1
            if shown < 20:
                print(row.rstrip('\n'))
                shown += 1
print('Matching entries:', found)
