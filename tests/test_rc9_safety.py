#!/usr/bin/env python3
"""RC9 coverage isolation smoke tests retained for RC10 regression checks."""
import os
import subprocess
import tempfile
import tarfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class CoverageTests(unittest.TestCase):
    def test_run_specific_isolation_and_exact_contig_match(self):
        for mode in ('PE','SE'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                base=Path(td); sample='TEST'; proj=base/'project'
                (proj/'04_assembly'/sample).mkdir(parents=True)
                (proj/'03_aligned').mkdir(parents=True)
                (proj/'tools').mkdir(parents=True)
                (proj/'04_assembly'/sample/('scaffolds.fasta' if mode=='PE' else 'contigs.fasta')).write_text('>NODE_1_length_5_cov_1\nAAAAA\n>NODE_10_length_5_cov_1\nAAAAA\n')
                (proj/'04_assembly'/sample/'finalviralhits.fasta').write_text('>NODE_1_length_5_cov_1\nAAAAA\n')
                (proj/'03_aligned'/(sample+'Unmapped.out.mate1.fastq.gz')).write_text('fake')
                (proj/'03_aligned'/(sample+'Unmapped.out.mate2.fastq.gz')).write_text('fake')
                (proj/'tools'/'getplots2.r').write_text('mock')
                t=(ROOT/'templates'/f'04_ViroXplore-HPC_v0.1_{mode}_remapping.sh.in').read_text()
                t=(t.replace('PUT_PATH_HERE',str(proj)).replace('PUT_SAMPLE_NAMES_HERE','("TEST")')
                     .replace('PUT_SLURM_PARTITION_HERE','pibu_el8').replace('PUT_ARRAY_HERE','1')
                     .replace('PUT_NUMBEROFSAMPLES_HERE','1'))
                script=base/'stage.sh';script.write_text(t)
                bin_dir=base/'bin';bin_dir.mkdir()
                programs={
                    'bowtie2-build':'#!/bin/bash\nexit 0\n',
                    'bowtie2':'#!/bin/bash\nwhile [[ $# -gt 0 ]]; do if [[ "$1" == -S ]]; then echo "x" > "$2"; exit 0; fi; shift; done\nexit 1\n',
                    'samtools':'#!/bin/bash\ncase "$1" in view) echo "alignments";; sort) while [[ $# -gt 0 ]]; do if [[ "$1" == -o ]]; then cat > "$2"; exit 0; fi; shift; done;; esac\n',
                    'bedtools':'#!/bin/bash\nprintf "NODE_1_length_5_cov_1\\t1\\t3\\nNODE_1_length_5_cov_1\\t2\\t4\\nNODE_10_length_5_cov_1\\t1\\t7\\n"\n',
                    'splitFileByColumn':'#!/bin/bash\nawk -F "\\t" \'{print > $1}\' "$1"\n',
                    'Rscript':'#!/bin/bash\nshopt -s nullglob\nfor f in NODE_*; do if [[ "$f" != *.pdf ]]; then echo "pdf" > "$f.pdf"; fi; done\n',
                }
                for name,body in programs.items():
                    exe=bin_dir/name;exe.write_text(body);exe.chmod(0o755)
                bash_env=base/'env.sh';bash_env.write_text('module() { return 0; }\n')
                env=dict(os.environ,PATH=str(bin_dir)+':'+os.environ['PATH'],
                         BASH_ENV=str(bash_env),SLURM_ARRAY_TASK_ID='1',SLURM_NPROCS='1')
                for jobid in ('9001','9002'):
                    env['SLURM_JOB_ID']=jobid
                    res=subprocess.run(['bash',str(script)],env=env,cwd=base,
                                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
                    self.assertEqual(res.returncode,0,res.stdout+'\n'+res.stderr)
                    work=proj/'06_remapping'/'tmp'/sample/(jobid+'_1')
                    self.assertTrue((work/'NODE_1_length_5_cov_1.pdf').is_file())
                    self.assertFalse((work/'NODE_10_length_5_cov_1.pdf').exists())
                    archive=proj/'06_remapping'/(sample+'viralhits_plots.tar.gz')
                    with tarfile.open(str(archive),'r:gz') as tfile:
                        names=tfile.getnames()
                        self.assertEqual(len(names),2)
                        self.assertFalse(any('NODE_10' in n for n in names))
                self.assertTrue((proj/'06_remapping'/'tmp'/sample/'9001_1').exists())
                self.assertTrue((proj/'06_remapping'/'tmp'/sample/'9002_1').exists())

if __name__=='__main__': unittest.main()
