#!/usr/bin/env python3
"""Offline integration smoke tests with mocked downloads and bioinformatics binaries."""
from pathlib import Path
import gzip
import os
import shutil
import subprocess
import tarfile
import tempfile

HERE = Path(__file__).resolve().parents[1]
DB = HERE / 'extras' / 'database_builder'


def executable(path, text):
    path.write_text('#!/usr/bin/env bash\nset -euo pipefail\n' + text)
    path.chmod(0o755)


def run(cmd, env, okay=True):
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if okay and p.returncode:
        raise AssertionError('%r exited %d\nSTDOUT: %s\nSTDERR: %s' % (cmd,p.returncode,p.stdout,p.stderr))
    if not okay and not p.returncode:
        raise AssertionError('Expected a failure: %r' % (cmd,))
    return p

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    fixtures = root/'fixtures'; fixtures.mkdir()
    (fixtures/'viral.1.1.genomic.fna.gz').write_bytes(gzip.compress(b'>NC_000001.1 some virus\nACGTAAAAAAAAAAGGTT\n'))
    (fixtures/'viral.1.genomic.gbff.gz').write_bytes(gzip.compress(b'''LOCUS       NC_000001            20 bp ss-RNA
DEFINITION  Mock virus reference genome.
ACCESSION   NC_000001
VERSION     NC_000001.1
FEATURES             Location/Qualifiers
     source          1..20
                     /db_xref="taxon:10239"
ORIGIN
        1 acgtgaaaaa aaaaggtt
//
'''))
    (fixtures/'prot.accession2taxid.FULL.gz').write_bytes(gzip.compress(b'accession.version\ttaxid\nAAA.1\t10239\n'))
    taxonomy = root/'tax-files'; taxonomy.mkdir()
    (taxonomy/'nodes.dmp').write_text('1\t|\t1\t|\tno rank\t|\n10239\t|\t1\t|\tsuperkingdom\t|\n')
    (taxonomy/'names.dmp').write_text('1\t|\troot\t|\t\t|\tscientific name\t|\n10239\t|\tViruses\t|\t\t|\tscientific name\t|\n')
    with tarfile.open(fixtures/'taxdump.tar.gz','w:gz') as z:
        for p in taxonomy.iterdir(): z.add(p, arcname=p.name)
    bindir=root/'bin'; bindir.mkdir()
    executable(bindir/'curl', '''
out=''; for ((i=1;i<=$#;i++)); do
  if [[ "${!i}" == --output ]]; then j=$((i+1)); out="${!j}"; fi
done
url="${*: -1}"
case "$url" in
 *viral.1.1.genomic.fna.gz) src="$FIXTURE_DIR/viral.1.1.genomic.fna.gz" ;;
 *viral.1.genomic.gbff.gz) src="$FIXTURE_DIR/viral.1.genomic.gbff.gz" ;;
 *prot.accession2taxid.FULL.gz) src="$FIXTURE_DIR/prot.accession2taxid.FULL.gz" ;;
 *taxdump.tar.gz) src="$FIXTURE_DIR/taxdump.tar.gz" ;;
 *) echo "unexpected curl URL $url" >&2; exit 1 ;;
esac
cp -- "$src" "$out"
''')
    executable(bindir/'bowtie2-build', '''
base="${*: -1}"
for suffix in 1 2 3 4 rev.1 rev.2; do printf 'MOCK\n' > "${base}.${suffix}.bt2"; done
''')
    executable(bindir/'dustmasker', '''
infile=''; outfile='';
while [[ $# -gt 0 ]]; do
 case "$1" in
 -in) infile="$2"; shift 2;;
 -out) outfile="$2"; shift 2;;
 *) shift;;
 esac
done
awk '/^>/ {print; next} {print tolower($0)}' "$infile" > "$outfile"
''')
    executable(bindir/'update_blastdb.pl', '''
printf 'MOCK\n' > nr.phr
''')
    executable(bindir/'blastdbcmd', '''
out=''
while [[ $# -gt 0 ]]; do
 case "$1" in
 -out) out="$2"; shift 2;;
 *) shift;;
 esac
done
printf '>AAA.1 mock virus protein\\nMAA\\n' > "$out"
''')
    executable(bindir/'diamond', '''
case "${1:-}" in
 version) echo 'diamond version 2.2.5';;
 dbinfo) if [[ "${FAIL_DBINFO:-0}" == 1 ]]; then exit 1; fi
         echo 'Database type Diamond database'; echo 'Sequences 1'; echo 'Letters 3';;
 *) exit 1;;
esac
''')
    # Replace only the heavyweight builder inside an isolated copy of its directory.
    mocked=root/'mockrepo'/'extras'/'database_builder'
    mocked.parent.mkdir(parents=True)
    shutil.copytree(DB,mocked,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(HERE/'tools', root/'mockrepo'/'tools', ignore=shutil.ignore_patterns('__pycache__'))
    (mocked/'build_viral_nr_all_v2.sh').write_text('''#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$OUTPUT_DIR"
printf 'MOCK DIAMOND\n' > "$OUTPUT_DIR/$DB_NAME.dmnd"
printf '{"fasta_records_kept":1}\n' > "$OUTPUT_DIR/$DB_NAME.filter_summary.json"
''')
    env=os.environ.copy(); env.update({'PATH':str(bindir)+os.pathsep+env.get('PATH',''),'FIXTURE_DIR':str(fixtures),'REFSEQ_FILE_URLS_LIST':str(root/'urls.txt')})
    (root/'urls.txt').write_text('https://ftp.ncbi.nlm.nih.gov/refseq/release/viral/viral.1.1.genomic.fna.gz\n')
    command=lambda op, dirname: ['bash',str(mocked/'setup_references.sh'),op,str(root/dirname)]
    run(command('refseq','success'),env)
    ref=root/'success'/'refseq_viral'/'refseq_viral.fna'
    assert ref.is_file() and (Path(str(ref)+'.masked.bed')).is_file()
    assert Path(str(ref)+'.10homopolymers.bed').read_text().strip().startswith('NC_000001.1')
    assert (root/'success'/'refseq_viral'/'contam_suppl_table_3.taxids.list').is_file()
    assert (root/'success'/'refseq_viral'/'refseq_viral_metadata.sqlite').is_file()
    run(command('nr','success'),env)
    assert (root/'success'/'viral_nr'/'viral_all_nr.dmnd').is_file()
    assert not (root/'success'/'nr_build_tmp'/'nr.faa').exists(), 'generated nr.faa should be deleted after verified success'
    assert not (root/'success'/'nr_build_tmp'/'blast_nr').exists(), 'downloaded BLAST volumes should be deleted after success'
    result = run(command('check','success'),env)
    assert 'OK RefSeq' in result.stdout and 'OK DIAMOND' in result.stdout
    env_fail=env.copy();env_fail['FAIL_DBINFO']='1'
    run(command('nr','failed'),env_fail,okay=False)
    assert (root/'failed'/'nr_build_tmp'/'nr.faa').is_file(), 'generated FASTA must survive a failed validation'
    assert (root/'failed'/'nr_build_tmp'/'blast_nr'/'nr.phr').is_file(), 'downloaded BLAST must survive a failed validation'
    supplied=root/'user_nr.faa';supplied.write_text('>AAA.1\nMAA\n')
    env_local=env.copy(); env_local['NR_LOCAL_FASTA']=str(supplied)
    run(command('nr','user_source'),env_local)
    assert supplied.is_file(), 'user-supplied FASTA must never be deleted'
    print('PASS: mock RefSeq download, Bowtie2, BED files, nr extraction, validated cleanup, failure retention, user FASTA protection')
