#!/usr/bin/env python3
"""Offline tests for RC7 PE/SE FASTQ preflight and master submission."""
from pathlib import Path
import contextlib
import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))
from preflight_reads import check_inputs


def gz(path):
    with gzip.open(str(path), 'wt') as handle:
        handle.write('@r1\nACGT\n+\nIIII\n')


class FastqTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'reads').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_pe(self):
        gz(self.root / 'reads' / 'fish_R1.fastq.gz')
        gz(self.root / 'reads' / 'fish_R2.fastq.gz')
        checked, warn = check_inputs(str(self.root), ['fish'], 'PE')
        self.assertEqual(len(checked), 2)
        self.assertEqual(warn, [])

    def test_missing_pe_r2_fails(self):
        gz(self.root / 'reads' / 'fish_R1.fastq.gz')
        with self.assertRaisesRegex(ValueError, 'R2 FASTQ missing'):
            check_inputs(str(self.root), ['fish'], 'PE')

    def test_zero_length_r2_fails(self):
        gz(self.root / 'reads' / 'fish_R1.fastq.gz')
        (self.root / 'reads' / 'fish_R2.fastq.gz').touch()
        with self.assertRaisesRegex(ValueError, 'R2 FASTQ is empty'):
            check_inputs(str(self.root), ['fish'], 'PE')

    def test_bad_gzip_fails(self):
        (self.root / 'reads' / 'fish_R1.fastq.gz').write_bytes(b'garbage')
        with self.assertRaisesRegex(ValueError, 'lacks gzip header'):
            check_inputs(str(self.root), ['fish'], 'SE')

    def test_se_warns_r2_present(self):
        gz(self.root / 'reads' / 'fish_R1.fastq.gz')
        gz(self.root / 'reads' / 'fish_R2.fastq.gz')
        checked, warn = check_inputs(str(self.root), ['fish'], 'SE')
        self.assertEqual(len(checked), 1)
        self.assertIn('will NOT be analysed', warn[0])

    def test_two_samples(self):
        for sample in ('a','b'):
            for mate in ('R1','R2'):
                gz(self.root / 'reads' / (sample+'_'+mate+'.fastq.gz'))
        checked, warn = check_inputs(str(self.root), ['a','b'], 'PE')
        self.assertEqual(len(checked), 4)


class MasterIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'ViroXplore-HPC'
        self.repo.mkdir()
        for file in ('ViroXplore-HPC_config.sh', 'ViroXplore-HPC_master.sh'):
            shutil.copy2(REPO/file, self.repo/file)
        for folder in ('tools', 'templates'):
            shutil.copytree(str(REPO/folder),str(self.repo/folder))
        self.project = self.root / 'project'
        (self.project / 'reads').mkdir(parents=True)
        gz(self.project/'reads'/'fish_R1.fastq.gz')
        gz(self.project/'reads'/'fish_R2.fastq.gz')
        (self.root/'host').mkdir()
        (self.root/'reference'/'refseq_viral').mkdir(parents=True)
        (self.root/'reference'/'refseq_viral'/'refseq_viral_metadata.sqlite').write_bytes(b'MOCK_OFFLINE_DB')
        self.mode='PE'

    def tearDown(self):
        self.tmp.cleanup()

    def configure(self, mode='PE', samples=('fish',)):
        cfg=self.repo/'ViroXplore-HPC_config.sh'
        value=cfg.read_text()
        values={
            'PROJECT_DIRECTORY':str(self.project),
            'SAMPLE_NAMES':'\'('+' '.join('"'+s+'"' for s in samples)+')\'',
            'HOST_GENOME':str(self.root/'host'),
            'REFERENCE_ROOT':str(self.root/'reference'),
            'NUMBEROFSAMPLES':str(len(samples)),
            'ARRAY':'1-'+str(len(samples)) if len(samples)>1 else '1',
            'SEQUENCING_MODE':mode,
            'SLURM_PARTITION':'pibu_el8',
        }
        for k,v in values.items():
            value, n=re.subn(r'^'+k+r'=.*$',lambda _:k+'='+v,value,count=1,flags=re.M)
            assert n==1,(k,n)
        cfg.write_text(value)
        r=subprocess.run(['bash',str(cfg)],cwd=str(self.repo),text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
        return r

    def runmaster(self,*args,env=None):
        return subprocess.run(['bash',str(self.repo/'ViroXplore-HPC_master.sh')]+list(args),cwd=str(self.repo),env=env,text=True,capture_output=True)

    def test_pe_dryrun_reports_mode(self):
        self.configure('PE')
        r=self.runmaster('--dry-run')
        self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
        self.assertIn('Sequencing mode: PE',r.stdout)
        self.assertIn('2 required files checked for 1 sample(s)',r.stdout)
        self.assertIn('DRY RUN:',r.stdout)
        self.assertFalse((self.repo/'pipeline_runs').exists())

    def test_missing_pe_r2_blocks_before_submit(self):
        self.configure('PE')
        (self.project/'reads'/'fish_R2.fastq.gz').unlink()
        r=self.runmaster()
        self.assertNotEqual(r.returncode,0)
        self.assertIn('R2 FASTQ missing',r.stderr)
        self.assertFalse((self.repo/'pipeline_runs').exists())

    def test_se_warning_if_r2_present(self):
        self.configure('SE')
        r=self.runmaster('--dry-run')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('Sequencing mode: SE',r.stdout)
        self.assertIn('1 required files checked for 1 sample(s)',r.stdout)
        self.assertIn('will NOT be analysed',r.stderr)

    def test_two_samples_requires_both_r2(self):
        gz(self.project/'reads'/'other_R1.fastq.gz')
        self.configure('PE', ('fish','other'))
        r=self.runmaster('--dry-run')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('other_R2.fastq.gz',r.stderr)
        gz(self.project/'reads'/'other_R2.fastq.gz')
        r=self.runmaster('--dry-run')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('4 required files checked for 2 sample(s)',r.stdout)

    def test_submit_five_jobs_with_valid_pe(self):
        self.configure('PE')
        fake=self.root/'bin'; fake.mkdir()
        invoked=self.root/'invocations.txt'
        script=fake/'sbatch'
        script.write_text('#!/bin/bash\necho "$@" >> "'+str(invoked)+'"\ncount=$(wc -l < "'+str(invoked)+'")\necho $((710000+count))\n')
        script.chmod(0o755)
        env=dict(os.environ,PATH=str(fake)+os.pathsep+os.environ.get('PATH',''))
        r=self.runmaster(env=env)
        self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
        self.assertIn('Sequencing mode: PE',r.stdout)
        self.assertEqual(len(invoked.read_text().splitlines()),5)
        calls=invoked.read_text().splitlines()
        self.assertTrue(all('--partition=pibu_el8' in call for call in calls))
        self.assertIn('--dependency=afterok:710001',calls[1])
        self.assertTrue((self.repo/'pipeline_runs').is_dir())

    def test_mode_switch_changes_stages(self):
        self.configure('PE')
        self.configure('SE')
        self.assertEqual(len(list(self.repo.glob('*_PE_*.sh'))),0)
        self.assertEqual(len(list(self.repo.glob('*_SE_*.sh'))),5)
        r=self.runmaster('--dry-run')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('Sequencing mode: SE',r.stdout)

if __name__ == '__main__':
    unittest.main()
