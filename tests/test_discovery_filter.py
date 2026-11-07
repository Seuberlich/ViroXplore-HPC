#!/usr/bin/env python3
"""Small offline regression suite for the viral discovery classifier."""
import csv
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from filter_discovery_hits import TaxonomyClassifier, run
from argparse import Namespace

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    tax = base / 'taxonomy'; tax.mkdir()
    rows = [
        (1,1,'root'), (131567,1,'cellular organisms'),
        (2,131567,'Bacteria'), (2157,131567,'Archaea'),
        (562,2,'Escherichia coli'),
        (10239,1,'Viruses'), (1001,10239,'Influenza A virus'),
        (1002,10239,'Equine rotavirus'),
        (1003,10239,'Bovine coronavirus'),
        (1004,10239,'Eastern equine encephalitis virus'),
        (1005,10239,'Shamonda virus'),
        (1006,10239,'Tobacco mosaic virus'),
        (1007,10239,'Mimivirus'),
        (1008,10239,'Unclassified RNA virus'),
        (2731619,10239,'Caudoviricetes'),
        (2001,2731619,'Escherichia phage lambda'),
        (2002,10239,'Sulfolobus spindle-shaped virus 1'),
        (2003,10239,'Pseudomonas phage P1'),
        (2004,10239,'Fuselloviridae'),
        (2005,2004,'novel archaeal virus'),
    ]
    with (tax/'nodes.dmp').open('w') as f:
        for ident, parent, _ in rows:
            f.write(f'{ident}\t|\t{parent}\t|\tno rank\t|\n')
    with (tax/'names.dmp').open('w') as f:
        for ident, _, name in rows:
            f.write(f'{ident}\t|\t{name}\t|\t\t|\tscientific name\t|\n')
    c = TaxonomyClassifier(tax)
    for taxid in range(1001,1009):
        assert c.one(taxid)[0] == 'keep', (taxid,c.one(taxid))
    for taxid in [2001,2002,2003,2004,2005,562]:
        assert c.one(taxid)[0] == 'exclude', (taxid,c.one(taxid))
    assert c.multi('1001;2001')[0] == 'review'
    assert c.multi('9999999')[0] == 'review'
    assert c.multi('0')[0] == 'review'
    assert c.multi('10239')[0] == 'review'

    fasta = base/'assembly.fasta'
    fasta.write_text('>NODE_1_length_9_cov_1.2\nATGATGATG\n'
                     '>NODE_2_length_9_cov_0.8\nTTTAAACCC\n'
                     '>NODE_3_length_9_cov_3.2\nATGTAGCTA\n')
    raw = base/'hits.tsv'
    lines = [
        ('NODE_1_length_9_cov_1.2','PHAGE001','2001','capsid protein [Escherichia phage]','85','99','1e-10','300'),
        ('NODE_1_length_9_cov_1.2','VIRUS001','1005','polymerase [Shamonda virus]','70','90','1e-9','250'),
        ('NODE_2_length_9_cov_0.8','VIRUS002','1003','spike [Bovine coronavirus]','92','120','1e-25','150'),
        ('NODE_3_length_9_cov_3.2','MIXED001','1001;2001','ambiguous nr protein','80','80','1e-8','140'),
        ('NODE_3_length_9_cov_3.2','UNKNOWN1','9999999','unclassified','80','80','1e-8','130'),
    ]
    raw.write_text('\n'.join('\t'.join(x) for x in lines)+'\n')
    result=base/'results'
    run(Namespace(taxonomy=str(tax),hits=str(raw),assembly=str(fasta),sample='TEST',output=str(result),final_fasta=str(base/'finalviralhits.fasta')))
    with (result/'TEST_DMNDtable_viruses_final.xls').open() as f:
        table = list(csv.DictReader(f, delimiter='\t'))
    assert len(table) == 2, table
    assert table[0]['id'] == 'NODE_1_length_9_cov_1.2'
    assert 'Shamonda' in table[0]['blastx_besthit']
    assert table[0]['nodelength'] == '9'
    assert table[0]['nodekmercov'] == '1.2'
    assert table[1]['id'] == 'NODE_2_length_9_cov_0.8'
    assert len(list(csv.DictReader((result/'TEST_DMND_hits_excluded.tsv').open(),delimiter='\t'))) == 1
    assert len(list(csv.DictReader((result/'TEST_DMND_hits_review.tsv').open(),delimiter='\t'))) == 2
    fasta_output=(base/'finalviralhits.fasta').read_text()
    assert fasta_output.count('>') == 2
    summary=json.loads((result/'TEST_DMND_filter_summary.json').read_text())
    assert summary['hit_decisions'] == {'exclude':1, 'keep':2, 'review':2}
    print('PASS: representative viruses retained; phage + archaeal excluded; ambiguous reviewed; best-hit after filter; FASTA and original 7-column table.')
