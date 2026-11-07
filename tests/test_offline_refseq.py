#!/usr/bin/env python3
"""Offline synthetic checks for RC10 RefSeq annotation (no external services)."""
import gzip
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'offline_ncbi_metadata.py'


def call(*args, ok=True):
    proc = subprocess.run([sys.executable, str(TOOL)] + list(map(str, args)),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)
    if ok and proc.returncode != 0:
        raise AssertionError('Expected success: {}\n{}'.format(args, proc.stderr))
    if not ok and proc.returncode == 0:
        raise AssertionError('Expected rejection: {}'.format(args))
    return proc


with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp)
    fasta = p / 'refseq_viral.fna'
    fasta.write_text('>NC_000001.1 first organism\nAAAA\n>NC_000002.1 other\nTTTT\n')
    nodes = p / 'nodes.dmp'
    nodes.write_text('1\t|\t1\t|\tno rank\t|\n10239\t|\t1\t|\tsuperkingdom\t|\n100\t|\t10239\t|\tspecies\t|\n200\t|\t10239\t|\tspecies\t|\n')
    names = p / 'names.dmp'
    names.write_text('1\t|\troot\t|\t\t|\tscientific name\t|\n10239\t|\tViruses\t|\t\t|\tscientific name\t|\n100\t|\tTest virus alpha\t|\t\t|\tscientific name\t|\n200\t|\tTest virus beta\t|\t\t|\tscientific name\t|\n')
    gbff = p / 'viral.1.genomic.gbff.gz'
    def entry(acc, tax, title):
        return (('LOCUS       ' + acc + ' 4 bp DNA\n' +
                 'DEFINITION  ' + title + '\n' +
                 '            complete genome.\n' +
                 'ACCESSION   ' + acc.split('.')[0] + '\n' +
                 'VERSION     ' + acc + '\n' +
                 'FEATURES             Location/Qualifiers\n' +
                 '     source          1..4\n' +
                 '                     /db_xref="taxon:' + str(tax) + '"\n' +
                 'ORIGIN\n        1 aaaa\n//\n'))
    with gzip.open(str(gbff), 'wt') as out:
        out.write(entry('NC_000001.1', 100, 'Alpha virus, isolate 5'))
        out.write(entry('NC_000002.1', 200, 'Beta virus'))
    db = p / 'offline.sqlite'
    build_args = ('build', '--reference-fasta', fasta, '--gbff', gbff,
                  '--nodes', nodes, '--names', names, '--database', db)
    result = call(*build_args)
    assert 'PASS: 2 / 2 FASTA references' in result.stdout, result.stdout
    with sqlite3.connect(str(db)) as con:
        assert con.execute('SELECT COUNT(*) FROM accessions').fetchone()[0] == 2
        assert con.execute('SELECT COUNT(*) FROM taxonomy').fetchone()[0] == 2
    accs = p / 'requested.list'
    accs.write_text('NC_000002.1\nNC_000001.1\n')
    out_acc = p / 'accessions.tsv'
    out_tax = p / 'taxonomy.tsv'
    lookup_args = ('lookup', '--database', db, '--reference-fasta', fasta,
                   '--accessions', accs, '--accession-output', out_acc,
                   '--taxonomy-output', out_tax)
    assert '2 unique identifiers' in call(*lookup_args).stdout
    assert out_acc.read_text().splitlines() == [
        'NC_000002.1\t200\tBeta virus complete genome.',
        'NC_000001.1\t100\tAlpha virus, isolate 5 complete genome.']
    assert out_tax.read_text().splitlines() == [
        '100\tTest virus alpha\tViruses', '200\tTest virus beta\tViruses']
    accs.write_text('NC_000001.1\nNC_999999.1\n')
    assert 'no local metadata' in call(*lookup_args, ok=False).stderr
    accs.write_text('NC_000001.1\n')
    fasta.write_text('>NC_000001.1 changed reference\nAAAT\n>NC_000002.1 other\nTTTT\n')
    assert 'DIFFERENT reference FASTA' in call(*lookup_args, ok=False).stderr
    fasta.write_text('>NC_000001.1\nAAAA\n>NC_000002.1\nTTTT\n>NC_000003.1\nCCCC\n')
    assert 'snapshot mismatch' in call(*build_args, ok=False).stderr
    assert db.exists() and db.stat().st_size > 0, 'original valid database must not be overwritten on failure'

# Make sure neither 02b template has runtime NCBI network calls or an array restriction.
for name in ('PE', 'SE'):
    path = ROOT / 'templates' / ('02b_ViroXplore-HPC_v0.5_' + name + '_mapping.sh.in')
    txt = path.read_text()
    for forbidden in ('module load EDirect', ' | esummary ', 'efetch -db taxonomy', '#SBATCH --array=PUT_ARRAY_HERE%1'):
        assert forbidden not in txt, (name, forbidden)
    assert 'offline_ncbi_metadata.py' in txt
print('PASS: offline RefSeq build, lookup, taxonomy, missing accession, snapshot consistency and PE/SE templates')
