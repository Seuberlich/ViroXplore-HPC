# ViroXplore-HPC v1.0.0 RC9 – PE and SE container validation

RC9 is a **candidate**. Local syntax / mock tests do not constitute an IBU end-to-end validation.
The RC7 FIX2 SIF remains unchanged at:
`/data/projects/p497_Sabbatical_Metagenomics/100_Container_Test/viroxplore-hpc_rc7_prototype.sif`.

## Key changes

- Stage 01: FastQC `--threads` and nonempty HTML/ZIP checks (PE and SE).
- Stage 04: every job receives a unique `06_remapping/tmp/SAMPLE/JOBID_TASKID/` scratch
  directory and exact matching of contig IDs from `finalviralhits.fasta`; the tarball
  contains **only** this job's coverage tables and PDFs. Produces
  `06_remapping/SAMPLE_coverage_runinfo.tsv` with plot counts. R/command failure
  returns a nonzero exit status.
- Stage 02b: fresh, per-job mapping/plot scratch directories and upstream NCBI EDirect (nuccore and taxonomy) is retried up to 3 times;
  accession completeness and TaxID metadata are validated. **If NCBI is unavailable
  and retries fail, 02b aborts intentionally**, to prevent silent loss of virus hits.
  This is *not* an offline NCBI metadata mode. Existing databases are not modified.

## Install and run

Extract RC9 to a **new folder**, for example:
`/data/projects/p497_Sabbatical_Metagenomics/100_Container_Test/RC9_validation/`.
Maintain two independent code folders `ViroXplore-HPC_PE` and `ViroXplore-HPC_SE`
and two independent output folders `PE` and `SE`. Both output folders must
contain `reads/` with the appropriate inputs. Do not place the new results on
existing RC8 outputs, even though stage 04 has isolation.

Set these values in each `ViroXplore-HPC_config.sh`:

```bash
SEQUENCING_MODE=PE  # or SE in the separate copy
EXECUTION_MODE=apptainer
SLURM_PARTITION=pibu_el8
CONTAINER_IMAGE=/data/projects/p497_Sabbatical_Metagenomics/100_Container_Test/viroxplore-hpc_rc7_prototype.sif
REFERENCE_ROOT=/data/projects/p2025-0064_small_ruminant_lentivirus/reference_databases
# PROJECT_DIRECTORY: new PE or SE output folder (with reads/)
# HOST_GENOME: the validated STAR host index for F17
# SAMPLE_NAMES='("F17_RNA_1Mio")', NUMBEROFSAMPLES=1, ARRAY=1
```

Run:

```bash
bash ViroXplore-HPC_config.sh
bash ViroXplore-HPC_master.sh --dry-run
bash ViroXplore-HPC_master.sh
```

Check after step 04:

```bash
cat /path/to/PE/06_remapping/F17_RNA_1Mio_coverage_runinfo.tsv
sacct -j JOBID --format=JobID,State,ExitCode,Elapsed
```

**Interpretation:** validate viral assignments by the discovery/RefSeq tables;
coverage plots alone cannot prove virus identity. PE and SE are two views of
one biological sample, not independent datasets. Compare against the successful
native F17 processing and original Hierweger et al., 2021 (PMID 34808081).

**Caveat:** A zero-candidate dataset may currently fail step 04 because no
`finalviralhits.fasta` candidates are available; this release targets positive
virus-discovery validation datasets and does not claim handling of all edge cases.

The configurator updates project `tools/` helpers if they differ, saving backup copies in the pipeline `.configuration_backups/` folder. The wrapper explicitly forwards `SLURM_JOB_ID` into Apptainer for unique run isolation.

## IBU example: safely running both modes in two new projects

Assuming the archive is in `100_Container_Test/`, run from that folder:

```bash
mkdir -p RC9_validation
cd RC9_validation
unzip ../ViroXplore-HPC_v1.0.0_RC9_Container_PE_SE_validation.zip
cp -a ViroXplore-HPC ViroXplore-HPC_PE
mv ViroXplore-HPC ViroXplore-HPC_SE
mkdir -p PE/reads SE/reads
```

Put R1/R2 FASTQ files (or symlinks to the existing, unchanged inputs) into
`PE/reads/`; put the **combined-read SE input** in `SE/reads/` named
`F17_RNA_1Mio_R1.fastq.gz`. Do not replace it by the original PE R1 alone.
Configure `PROJECT_DIRECTORY` and `SEQUENCING_MODE` independently in each
pipeline copy. Keep the earlier native and RC8 results in place for comparison.

Verify all five array-task SLURM statuses, not only the final artifact counts.
When EDirect is unreachable, step 02b now exits with an explicit error instead
of silently dropping unannotated viral mapping rows. Rerun only after the
network is available; a future offline taxonomy mode can remove this dependency.
