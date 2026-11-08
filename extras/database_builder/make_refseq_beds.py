#!/usr/bin/env python3
"""Create zero-based, half-open BED intervals for DUST masks and homopolymers.

Requires identical FASTA sequence IDs and lengths between original and dustmasked.
Bacterial/archaeal viruses are not removed from the RefSeq nucleotide collection.
"""
import argparse
from itertools import zip_longest

def fasta_records(path):
    label = None
    pieces = []
    with open(path, 'r', encoding='ascii') as src:
        for row in src:
            row = row.rstrip('\r\n')
            if row.startswith('>'):
                if label is not None:
                    yield label, ''.join(pieces)
                label = row[1:].split()[0]
                if not label:
                    raise ValueError('Empty FASTA record identifier')
                pieces = []
            elif row:
                if label is None:
                    raise ValueError('FASTA sequence encountered before header')
                pieces.append(row.strip())
    if label is not None:
        yield label, ''.join(pieces)

def masked_ranges(s):
    start = None
    for i, ch in enumerate(s):
        if ch.islower():
            if start is None:
                start = i
        elif start is not None:
            yield start, i
            start = None
    if start is not None:
        yield start, len(s)

def homopolymer_ranges(s, minimum=10):
    s = s.upper()
    start = 0
    for i in range(1, len(s) + 1):
        if i == len(s) or s[i] != s[start]:
            if s[start] in 'ACGT' and i-start >= minimum:
                yield start, i
            start = i

def build(original, masked, masked_bed, homopolymer_bed):
    count = 0
    with open(masked_bed, 'w') as m, open(homopolymer_bed, 'w') as h:
        for left, right in zip_longest(fasta_records(original), fasta_records(masked)):
            if left is None or right is None:
                raise ValueError('Original and DUST FASTA have different record counts')
            seq_id, sequence = left
            mid, masked_sequence = right
            if seq_id != mid or len(sequence) != len(masked_sequence):
                raise ValueError('Original/DUST FASTA accession or sequence length mismatch: %s / %s' % (seq_id, mid))
            for start, end in masked_ranges(masked_sequence):
                m.write('%s\t%d\t%d\n' % (seq_id, start, end))
            for start, end in homopolymer_ranges(sequence):
                h.write('%s\t%d\t%d\n' % (seq_id, start, end))
            count += 1
    if count == 0:
        raise ValueError('No FASTA sequences found')
    return count

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--masked', required=True)
    p.add_argument('--low-complexity-bed', required=True)
    p.add_argument('--homopolymers-bed', required=True)
    a = p.parse_args()
    n = build(a.input, a.masked, a.low_complexity_bed, a.homopolymers_bed)
    print('ViroXplore-HPC: generated BED files for %d sequences' % n)

if __name__ == '__main__':
    main()
