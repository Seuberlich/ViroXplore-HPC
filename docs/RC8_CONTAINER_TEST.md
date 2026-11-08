# ViroXplore-HPC RC8: Full PE and SE Apptainer validation

This RC8 test candidate extends RC7 FIX2 with **one central execution selector**.
The scientific stage bodies are identical to RC7; native execution remains the default.
Use the **master** to launch containerized stages. Launching an original `01_*.sh`
directly bypasses the Apptainer backend; generated `.apptainer_stage_*.sbatch`
files are the container-specific SLURM launchers.

## Existing image

`/data/projects/p497_Sabbatical_Metagenomics/100_Container_Test/viroxplore-hpc_rc7_prototype.sif`

Image was built with RC7 FIX2. This RC8 package does not rebuild the image.
The container is experimental; tool versions differ from native IBU software.

## Data setup

Create two **separate** projects, e.g.
`/data/projects/p497_Sabbatical_Metagenomics/100_Container_Test/validation_PE`
and `.../validation_SE`. Each project must have `reads/` containing its own
`F17_RNA_1Mio_R1.fastq.gz` and, for PE, `F17_RNA_1Mio_R2.fastq.gz`.
For SE, use the same validated read representation as the earlier SE test.
Do not point PE and SE at one output directory. Avoid symlinking the *project*
directories; read-file symlinks on shared `/data` are fine if accessible.

## Before each run

In `ViroXplore-HPC_config.sh`, set:

```bash
PROJECT_DIRECTORY=/data/projects/p497_Sabbatical_Metagenomics/100_Container_Test/validation_PE
SAMPLE_NAMES='("F17_RNA_1Mio")'
NUMBEROFSAMPLES=1
ARRAY=1
SEQUENCING_MODE=PE
EXECUTION_MODE=apptainer
SLURM_PARTITION=pibu_el8
CONTAINER_IMAGE=/data/projects/p497_Sabbatical_Metagenomics/100_Container_Test/viroxplore-hpc_rc7_prototype.sif
REFERENCE_ROOT=/data/projects/p2025-0064_small_ruminant_lentivirus/reference_databases
HOST_GENOME=/ABSOLUTE/PATH/TO/YOUR/EXISTING/STAR_INDEX
```

Use a clean copy of this RC8 pipeline folder for EACH mode (e.g. `ViroXplore-HPC_PE`
and `ViroXplore-HPC_SE`) to preserve manifests and scripts across both runs.

```bash
bash ViroXplore-HPC_config.sh
bash ViroXplore-HPC_master.sh --dry-run
bash ViroXplore-HPC_master.sh
```

For SE change only `PROJECT_DIRECTORY` and `SEQUENCING_MODE=SE` while keeping
corresponding `SAMPLE_NAMES` and input FASTQ naming consistent.

## Checks and warnings

- The master validates PE R1/R2 existence and reports selected mode and image.
- Container wrappers inherit exactly the original stage SLURM directives.
- Apptainer is called **on compute nodes**, not on login nodes.
- A non-zero stage status blocks dependent stages; some legacy stage scripts do
  not use `set -e` and may not propagate every subcommand failure, so **inspect
  all stage log files and expected outputs**, not only SLURM COMPLETED.
- Pre-existing STAR host indices may be incompatible with the new container STAR
  version. STAR will report this in the step-01 logs. The original host indices
  are never modified.
- Step 02b queries NCBI EDirect. Compute nodes need network access for these
  requests; otherwise step 02b will need an offline-mode enhancement.
- Prefer testing with output-free projects, not reusing old results; stages 01/02a
  can encounter existing files/directories on reruns.
- The container's R/other versions differ from native and plotting may need fixes.
- Build FIX2 smoke test checks executables, not the complete workflow.

On completion, upload PE and SE `.o/.e` logs, mapping tables, `05_discovery`
results and `06_remapping` outputs for validation against the native runs.
