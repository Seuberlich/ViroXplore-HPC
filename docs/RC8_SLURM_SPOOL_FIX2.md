# RC8 SLURM spool-path correction (FIX2)

## Failure

When an Apptainer wrapper is submitted with `sbatch`, SLURM copies the
batch script to a private spool directory such as
`/var/spool/slurmd/job20839193/slurm_script`.
The previous generated wrappers computed `HERE` using `BASH_SOURCE[0]`,
which pointed to the spool directory. As a result, the wrapper attempted to
start `.../job20839193/container/run_stage_apptainer.sh`, which does not exist.

## Correction

The central configurator now embeds the absolute path to the configured
pipeline root when generating `.apptainer_stage_*.sbatch` files. This remains
correct even if SLURM copies those scripts to another directory.
No bioinformatics algorithm, PE/SE analysis stage, reference database, or
Apptainer image has changed.

## Existing customized PE or SE installation

Place `repair_RC8_SLURM_spool_FIX2.py` into the existing PE or SE pipeline
directory, then run:

```bash
python3 repair_RC8_SLURM_spool_FIX2.py
```

The repair script backs up the existing customized configurator, changes only
the wrapper generation line, re-runs configuration (which regenerates the
five wrappers and their checksums) and finally performs the master dry-run.
It preserves all project paths and settings. Repeat separately for both PE and
SE pipeline directories.

Alternatively, replace the existing configurator with the FIX2 version,
copy the existing settings across manually, then run the configurator and
master dry-run.

After checking and cancelling any obsolete dependent SLURM jobs from the
failed run, submit a fresh master job:

```bash
bash ViroXplore-HPC_master.sh
```

Never launch the pipeline from a login node manually outside SLURM.

## Tests

An integration test copies a configured stage wrapper to a simulated
`var/spool/slurmd/job20839193/slurm_script` and executes it using a mocked
Apptainer command. The test ensures the absolute image and stage paths are
passed successfully. All existing native/Apptainer PE/SE, reference and
discovery tests also pass.
