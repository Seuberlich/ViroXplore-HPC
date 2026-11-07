#!/usr/bin/env python3
"""Conservative offline exclusion of identifiable bacteriophages from RefSeq result tables.

Only annotation tables are filtered; BAM files and mapping statistics are untouched.
The local accession title and taxonomic scientific name are searched for phage
terminology. Entries without such annotations cannot reliably be host-classified.
Python >=3.6; standard library only.
"""
import argparse
import re
import sys

PHAGE = re.compile(r"(?:bacterio|pro)?phage", re.IGNORECASE)


def filter_tables(accession_input, taxonomy_input, accession_output, taxonomy_output):
    taxa = {}
    with open(taxonomy_input, encoding='utf-8') as inp:
        for line in inp:
            fields = line.rstrip('\n').split('\t')
            if len(fields) < 3:
                raise ValueError('Malformed taxonomy annotation row')
            taxa[fields[0]] = fields
    kept = set()
    removed = 0
    with open(accession_input, encoding='utf-8') as inp, open(accession_output, 'w', encoding='utf-8') as out:
        for line in inp:
            fields = line.rstrip('\n').split('\t', 2)
            if len(fields) != 3 or fields[1] not in taxa:
                raise ValueError('Malformed or unmatched accession annotation row')
            if PHAGE.search(fields[2]) or PHAGE.search(taxa[fields[1]][1]):
                removed += 1
                continue
            out.write(line)
            kept.add(fields[1])
    with open(taxonomy_output, 'w', encoding='utf-8') as out:
        for taxid in sorted(kept, key=int):
            out.write('\t'.join(taxa[taxid]) + '\n')
    print('Offline phage annotation filter: excluded {} accession(s)'.format(removed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accession-input', required=True)
    parser.add_argument('--taxonomy-input', required=True)
    parser.add_argument('--accession-output', required=True)
    parser.add_argument('--taxonomy-output', required=True)
    a = parser.parse_args()
    filter_tables(a.accession_input, a.taxonomy_input, a.accession_output, a.taxonomy_output)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as e:
        sys.exit('ERROR: ' + str(e))
