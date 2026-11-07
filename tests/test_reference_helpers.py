#!/usr/bin/env python3
"""Offline tests for the optional reference database setup helpers."""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'extras' / 'database_builder'))
from discover_refseq_files import discover
from make_refseq_beds import build

BASE = 'https://ftp.ncbi.nlm.nih.gov/refseq/release/viral/'
html = '''<html><a href="viral.1.1.genomic.fna.gz">ref 1</a>
<a href="viral.2.1.genomic.fna.gz">ref 2</a>
<a href="viral.1.protein.faa.gz">proteins</a>
<a href="https://evil.example/viral.3.1.genomic.fna.gz">evil</a></html>'''
assert discover(BASE, html) == [BASE+'viral.1.1.genomic.fna.gz', BASE+'viral.2.1.genomic.fna.gz']
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    original = root/'original.fna'
    masked = root/'dust.fna'
    low = root/'masked.bed'
    homo = root/'homopolymers.bed'
    original.write_text('>NC_000001.1 first\nGGGAAAAAAAAAATTTGG\n>NC_000002.1\nACGTGGGGGGGGGGAC\n')
    masked.write_text('>NC_000001.1 first\nGGGaaaaaaaaaaTTTGG\n>NC_000002.1\nACGTGGGGGGGGGGAC\n')
    assert build(str(original),str(masked),str(low),str(homo)) == 2
    assert low.read_text().strip() == 'NC_000001.1\t3\t13'
    assert homo.read_text().splitlines() == ['NC_000001.1\t3\t13','NC_000002.1\t4\t14']
    masked.write_text('>NC_000002.1\nAAAA\n')
    try:
        build(str(original),str(masked),str(low),str(homo))
    except ValueError:
        pass
    else:
        raise AssertionError('Mismatched FASTA records must fail')
print('PASS: RefSeq discovery, 0-based BED, 10-nt homopolymers, mismatched-record guard')
