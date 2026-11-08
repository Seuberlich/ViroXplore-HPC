#!/usr/bin/env python3
"""Regression: composite viral GenBank records must use primary organism TaxID."""
import gzip
import importlib.util
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / 'tools' / 'offline_ncbi_metadata.py'
spec = importlib.util.spec_from_file_location('offline_ncbi_metadata', str(TOOL))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def record(version, primary, sources):
    txt = ('LOCUS       {} 16 bp RNA\n'
           'DEFINITION  Composite reference sequence.\n'
           'SOURCE      {}\n'
           '  ORGANISM  {}\n'
           '            Viruses.\n'
           'ACCESSION   {}\n'
           'VERSION     {}\n'
           'FEATURES             Location/Qualifiers\n').format(
                version, primary, primary, version.split('.')[0], version)
    for i, (name, taxid) in enumerate(sources):
        txt += ('     source          {}..{}\n'
                '                     /organism="{}"\n'
                '                     /db_xref="taxon:{}"\n').format(
                    1 + 8*i, 8 + 8*i, name, taxid)
    return txt + 'ORIGIN\n        1 aaaa\n//\n'

with tempfile.TemporaryDirectory() as td:
    gbff = Path(td) / 'viral.genomic.gbff.gz'
    with gzip.open(str(gbff), 'wt') as out:
        # The first source is deliberately NOT the primary source.
        out.write(record('NC_043404.1', 'Avian myeloblastosis virus',
                         [('Gallus gallus', 9031), ('Avian myeloblastosis virus', 11866)]))
        out.write(record('NC_000001.1', 'One source virus', [('One source virus', 100)]))
    rows = list(mod.read_gbff_records(gbff))
    assert rows[0][1] == 11866, rows
    assert rows[1][1] == 100, rows
    with gzip.open(str(gbff), 'wt') as out:
        out.write(record('NC_000003.1', 'Unknown primary organism',
                         [('Alpha virus', 101), ('Beta virus', 102)]))
    try:
        list(mod.read_gbff_records(gbff))
    except ValueError as exc:
        assert 'cannot be resolved unambiguously' in str(exc), exc
    else:
        raise AssertionError('Ambiguous primary TaxID silently accepted')

    with gzip.open(str(gbff), 'wt') as out:
        out.write(record('NC_000004.1', 'Two same-name primary organism',
                         [('Two same-name primary organism', 101),
                          ('Two same-name primary organism', 102)]))
    try:
        list(mod.read_gbff_records(gbff))
    except ValueError as exc:
        assert 'cannot be resolved unambiguously' in str(exc), exc
    else:
        raise AssertionError('Conflicting primary TaxIDs silently accepted')
# A primary organism may have a species-level and an isolate-level TaxID.
# NCBI taxonomy lineage, not the arbitrary first source, resolves the tie.
parents = {1: 1, 10239: 1, 180504: 10239, 2883940: 180504, 9031: 1}
with tempfile.TemporaryDirectory() as td:
    gbff = Path(td) / 'hierarchical.gbff.gz'
    with gzip.open(str(gbff), 'wt') as out:
        out.write(record('NC_003309.1', 'Burkholderia phage phiE125',
                         [('Burkholderia phage phiE125', 180504),
                          ('Burkholderia phage phiE125', 2883940)]))
    assert list(mod.read_gbff_records(gbff, parents))[0][1] == 2883940
    # Without a loaded hierarchy, retain FIX1's fail-closed behavior.
    try:
        list(mod.read_gbff_records(gbff))
    except ValueError as exc:
        assert 'cannot be resolved unambiguously' in str(exc)
    else:
        raise AssertionError('Missing taxonomy hierarchy silently accepted')
    # A non-related primary TaxID must never be selected arbitrarily.
    with gzip.open(str(gbff), 'wt') as out:
        out.write(record('NC_000008.1', 'Test virus',
                         [('Test virus', 180504), ('Test virus', 9031)]))
    try:
        list(mod.read_gbff_records(gbff, parents))
    except ValueError as exc:
        assert 'cannot be resolved unambiguously' in str(exc)
    else:
        raise AssertionError('Divergent taxonomy lineages silently accepted')

print('PASS: primary TaxIDs, hierarchical TaxID resolution, divergent and ambiguous records')
