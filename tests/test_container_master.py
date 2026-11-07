#!/usr/bin/env python3
"""Offline RC8 integration tests: native/Apptainer, PE/SE SLURM launchers."""
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]


def gz(path):
    with gzip.open(path,'wt') as f:
        f.write('@r\nACGT\n+\nIIII\n')

class RC8Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.repo=self.base/'ViroXplore-HPC'
        shutil.copytree(SOURCE,self.repo,ignore=shutil.ignore_patterns('.pipeline_configuration.json','*.sh.bak_*','__pycache__','.configuration_backups'))
        self.project=self.base/'project'
        (self.project/'reads').mkdir(parents=True)
        gz(self.project/'reads'/'F17_RNA_1Mio_R1.fastq.gz')
        gz(self.project/'reads'/'F17_RNA_1Mio_R2.fastq.gz')
        (self.base/'host').mkdir(); (self.base/'ref'/'refseq_viral').mkdir(parents=True)
        (self.base/'ref'/'refseq_viral'/'refseq_viral_metadata.sqlite').write_bytes(b'MOCK_METADATA')
        self.image=self.base/'fish image.sif'  # Path with whitespace correctly rejected
        self.validimage=self.base/'image.sif'; self.validimage.write_bytes(b'SIF-TEST')

    def configure(self, mode, execution):
        cfg=self.repo/'ViroXplore-HPC_config.sh'
        s=cfg.read_text()
        parameters={
            'PROJECT_DIRECTORY':str(self.project),
            'SAMPLE_NAMES':"'(\"F17_RNA_1Mio\")'",
            'HOST_GENOME':str(self.base/'host'),
            'REFERENCE_ROOT':str(self.base/'ref'),
            'NUMBEROFSAMPLES':'1',
            'ARRAY':'1',
            'SEQUENCING_MODE':mode,
            'SLURM_PARTITION':'pibu_el8',
            'EXECUTION_MODE':execution,
            'CONTAINER_IMAGE':str(self.validimage),
        }
        for key,val in parameters.items():
            s,n=re.subn(r'^'+key+r'=.*$',lambda _:key+'='+val,s,count=1,flags=re.M)
            self.assertEqual(n,1)
        cfg.write_text(s)
        p=subprocess.run(['bash',str(cfg)],cwd=self.repo,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        return p

    def master(self,dryrun=False, submit=False):
        env=dict(os.environ)
        logfile=self.base/'sbatch_invocations.log'
        if submit:
            fakebin=self.base/'bin'; fakebin.mkdir(exist_ok=True)
            script=fakebin/'sbatch'
            script.write_text('#!/bin/bash\necho "$@" >> "'+str(logfile)+'"\ncount=$(wc -l < "'+str(logfile)+'")\necho $((500000 + count))\n')
            script.chmod(0o755)
            env['PATH']=str(fakebin)+':'+env['PATH']
        result=subprocess.run(['bash',str(self.repo/'ViroXplore-HPC_master.sh')]+(['--dry-run'] if dryrun else []),cwd=self.repo,env=env,text=True,capture_output=True)
        return result, logfile

    def test_pe_container_dryrun_and_submission(self):
        self.configure('PE','apptainer')
        r,_=self.master(dryrun=True)
        self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
        self.assertIn('Execution mode: apptainer',r.stdout)
        self.assertIn('Sequencing mode: PE',r.stdout)
        wrappers=list(self.repo.glob('.apptainer_stage_*.sbatch'))
        self.assertEqual(len(wrappers),5)
        for name in ['01','02a','02b','03','04']:
            wrapper=self.repo/f'.apptainer_stage_{name}.sbatch'
            self.assertIn('exec /bin/bash "$HERE/container/run_stage_apptainer.sh"',wrapper.read_text())
            self.assertIn('HERE='+str(self.repo.resolve())+'\n',wrapper.read_text())
            self.assertNotIn('BASH_SOURCE',wrapper.read_text())
            self.assertIn('--partition=pibu_el8',wrapper.read_text())
            self.assertIn(self.validimage.as_posix(),wrapper.read_text())
        r,log=self.master(submit=True)
        self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
        calls=log.read_text().splitlines()
        self.assertEqual(len(calls),5)
        for i,s in enumerate(['01','02a','02b','03','04']):
            self.assertIn('.apptainer_stage_'+s+'.sbatch',calls[i])
            self.assertIn('--partition=pibu_el8',calls[i])
            if i: self.assertIn('--dependency=afterok:'+str(500000+i),calls[i])

    def test_se_container_and_mode_switch(self):
        self.configure('PE','apptainer')
        self.configure('SE','apptainer')
        r,_=self.master(dryrun=True)
        self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
        self.assertIn('Sequencing mode: SE',r.stdout)
        self.assertIn('will NOT be analysed',r.stderr)
        self.assertEqual(len(list(self.repo.glob('*_SE_*.sh'))),5)
        self.assertEqual(len(list(self.repo.glob('*_PE_*.sh'))),0)
        self.assertEqual(len(list(self.repo.glob('.apptainer_stage_*.sbatch'))),5)

    def test_native_mode_stays_native(self):
        self.configure('PE','apptainer')
        self.configure('PE','native')
        r,log=self.master(submit=True)
        self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
        self.assertIn('Execution mode: native',r.stdout)
        self.assertEqual(len(list(self.repo.glob('.apptainer_stage_*.sbatch'))),0)
        self.assertEqual(len(list(self.repo.glob('*_PE_*.sh'))),5)
        self.assertNotIn('.apptainer_stage_',log.read_text())

    def test_missing_image_fails_configuration(self):
        self.validimage.unlink()
        cfg=self.repo/'ViroXplore-HPC_config.sh'
        t=cfg.read_text().replace('EXECUTION_MODE=native','EXECUTION_MODE=apptainer')
        t=t.replace('CONTAINER_IMAGE=/data/projects/p497_Sabbatical_Metagenomics/100_Container_Test/viroxplore-hpc_rc7_prototype.sif',f'CONTAINER_IMAGE={self.validimage}')
        t=t.replace('PROJECT_DIRECTORY=/absolute/path/to/my_project',f'PROJECT_DIRECTORY={self.project}')
        t=t.replace('HOST_GENOME=/absolute/path/to/STAR_genome_index',f'HOST_GENOME={self.base}/host')
        t=t.replace('REFERENCE_ROOT=/absolute/path/to/reference_databases',f'REFERENCE_ROOT={self.base}/ref')
        cfg.write_text(t)
        p=subprocess.run(['bash',str(cfg)],cwd=self.repo,text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('CONTAINER_IMAGE does not exist',p.stderr+p.stdout)

    def test_missing_pe_r2_fails_before_submit(self):
        self.configure('PE','apptainer')
        (self.project/'reads'/'F17_RNA_1Mio_R2.fastq.gz').unlink()
        r,log=self.master(submit=True)
        self.assertNotEqual(r.returncode,0)
        self.assertIn('R2 FASTQ missing',r.stderr)
        self.assertFalse(log.exists())

    def test_wrapper_uses_apptainer_inside_slurm_allocation(self):
        self.configure('PE','apptainer')
        fakebin=self.base/'bin';fakebin.mkdir()
        log=self.base/'apptainer_args.txt'
        (fakebin/'apptainer').write_text('#!/bin/bash\nprintf "%s\\n" "$@" > '+str(log)+'\n')
        (fakebin/'apptainer').chmod(0o755)
        env=dict(os.environ,PATH=str(fakebin)+':'+os.environ['PATH'],SLURM_JOB_ID='12345',SLURM_ARRAY_TASK_ID='1')
        wrapper=self.repo/'.apptainer_stage_01.sbatch'
        p=subprocess.run(['bash',str(wrapper)],env=env,cwd=self.repo,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        args=log.read_text()
        self.assertIn('exec\n--cleanenv',args)
        self.assertIn(self.validimage.as_posix(),args)
        self.assertIn('01_ViroXplore-HPC_v0.1_PE_qc_trim_hostrm.sh',args)

    def test_slurm_spooled_wrapper_resolves_pipeline_root(self):
        # SLURM executes a COPY of .sbatch under /var/spool/slurmd/job...;
        # the wrapper must NOT derive its directory from BASH_SOURCE[0].
        self.configure('PE','apptainer')
        fakebin=self.base/'bin'; fakebin.mkdir()
        log=self.base/'apptainer_spooled_args.txt'
        (fakebin/'apptainer').write_text('#!/bin/bash\nprintf "%s\\n" "$@" > '+str(log)+'\n')
        (fakebin/'apptainer').chmod(0o755)
        env=dict(os.environ,PATH=str(fakebin)+':'+os.environ['PATH'],
                 SLURM_JOB_ID='20839193',SLURM_ARRAY_TASK_ID='1')
        spool=self.base/'var/spool/slurmd/job20839193'
        spool.mkdir(parents=True)
        spooled_script=spool/'slurm_script'
        shutil.copy2(str(self.repo/'.apptainer_stage_01.sbatch'),str(spooled_script))
        result=subprocess.run(['bash',str(spooled_script)],env=env,cwd=self.base,
                              universal_newlines=True,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        args=log.read_text()
        self.assertIn('exec\n--cleanenv',args)
        self.assertIn(str(self.repo/'01_ViroXplore-HPC_v0.1_PE_qc_trim_hostrm.sh'),args)
        self.assertIn(self.validimage.as_posix(),args)

if __name__=='__main__': unittest.main()
