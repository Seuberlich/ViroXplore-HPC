# Upgrading to RC7 from RC6

RC7 keeps the RC6 `SLURM_PARTITION`, `REFERENCE_ROOT`, master dependency chain,
reference builder and scientific analysis steps. It adds mode-specific input
checks, especially for paired-end FASTQ submissions.

1. Unpack RC7 into a **new software directory**; preserve the old RC6
   installation and project results until validation.
2. Copy local values (`PROJECT_DIRECTORY`, `SAMPLE_NAMES`, `HOST_GENOME`,
   `NUMBEROFSAMPLES`, `ARRAY`, `REFERENCE_ROOT`, `SLURM_PARTITION`,
   `SEQUENCING_MODE`, `NOTIFICATION_EMAIL`) into `ViroXplore-HPC_config.sh`.
3. In `PROJECT_DIRECTORY/reads/`, place `SAMPLE_R1.fastq.gz` and for PE
   `SAMPLE_R2.fastq.gz` for every sample in `SAMPLE_NAMES`.
4. Run `bash ViroXplore-HPC_config.sh`.
5. Run `bash ViroXplore-HPC_master.sh --dry-run` and confirm the printed
   mode and preflight result. Do **not** run PE and SE in the same output
   directory unless you explicitly intend to replace previous results.
6. Run `bash ViroXplore-HPC_master.sh` to submit five dependent jobs.

An SE dry-run warns if corresponding R2 files are present but not used.
A PE dry-run stops before submission if either mate is missing or empty.
Fast gzip-header checks do not establish full FASTQ integrity or pairing.
Direct `sbatch` execution of stage 01 also verifies its input file presence.

**RC7 has not been end-to-end tested on a real HPC in this package.**
For a genuine PE validation check fastp `-i` and `-I`, STAR two read files,
SPAdes `--pe1-1/--pe1-2`, Bowtie2 `-1/-2`, and discovery `mode: PE` in job logs.
