# Installation and operation

## 1. Obtain the software and plan the deployment

Copy the repository to a Linux HPC login node with SLURM and Modules. A normal desktop/laptop is not the intended target for the full workflow.

The **software directory** containing `ViroXplore-HPC_master.sh`, `templates/`, `tools/` and `ViroXplore-HPC_config.sh` can be located anywhere accessible to the login node. Separately create a **project directory** with a `reads/` subdirectory.

Expected input filenames, where SAMPLE is a name listed in `SAMPLE_NAMES`:

| Mode | Required input files in PROJECT_DIRECTORY/reads/ |
| --- | --- |
| PE | `SAMPLE_R1.fastq.gz` and `SAMPLE_R2.fastq.gz` |
| SE | `SAMPLE_R1.fastq.gz` |

These filename patterns reflect the actual current stage-01 templates, not a general FASTQ naming convention.

> **Library preparation warning:** Stage-01 `fastp` trimming parameters are tailored to the Lexogen CORALL Total RNA library preparations used during validation. They are not general-purpose settings. Review the [library-specific trimming guide](LIBRARY_SPECIFIC_TRIMMING.md) and adapt the relevant PE/SE stage-01 template before configuration for other library types.

## 2. Prepare external dependencies and databases

Install or load the required tools on the cluster. Update cluster-specific `module load` lines in `templates/*.sh.in` **before running the configurator**. Set `SLURM_PARTITION` in the central configurator; do not edit the partition placeholder in the templates. The `MODULE_*` variables at the beginning of several templates are documentary; verify the actual `module load` commands executed farther down.

Prepare the nucleotide (Bowtie2) and protein (DIAMOND) viral databases under one shared reference root using the optional installer:

```bash
# In a sufficiently provisioned HPC batch allocation:
bash extras/database_builder/setup_references.sh all /absolute/path/to/reference_databases
```

You may also prepare those files manually; see [REFERENCE_DATABASES.md](REFERENCE_DATABASES.md) for expected filenames, the required BED files and the optional contamination TaxID list. The database installer is separate from the five-stage master and requires extensive temporary disk space.

The configurator now propagates `REFERENCE_ROOT` into stages 02b and 03. It should point to the exact output root from the installer. The STAR host index remains an independent setting.

### Apptainer execution

Set `EXECUTION_MODE=apptainer` in `ViroXplore-HPC_config.sh` and replace the example `CONTAINER_IMAGE=/absolute/path/to/viroxplore-hpc.sif` with the **absolute path of an existing SIF file** on your cluster. The default `EXECUTION_MODE=native` uses host modules instead. The configurator checks that the SIF exists and refuses to generate container-mode jobs for a nonexistent image. The ZIP package does **not** contain a `.sif`; build or obtain it separately using the container instructions in `container/README.md`. The IBU test image name and storage location are deployment-specific and are deliberately not packaged as defaults.

## 3. Configure the five stages

Open `ViroXplore-HPC_config.sh` and edit the variables at the top, for example:

```bash
PROJECT_DIRECTORY=/absolute/path/to/my_project
SAMPLE_NAMES='("Sample1" "Sample2")'
HOST_GENOME=/absolute/path/to/STAR_genome_index
REFERENCE_ROOT=/absolute/path/to/reference_databases
NUMBEROFSAMPLES=2
ARRAY=1-2
SLURM_PARTITION=pibu_el8
SEQUENCING_MODE=PE
EXECUTION_MODE=apptainer
CONTAINER_IMAGE=/absolute/path/to/viroxplore-hpc.sif
NOTIFICATION_EMAIL="user@example.org"
```

**Important:** `SLURM_PARTITION` must be an existing partition accessible to your account (list partitions with `sinfo -o "%P %a %l %D"`). The configurator injects it into all selected analysis scripts and the master submits every step with the explicit `--partition` option. Partition time and memory limits must be sufficient for each stage. `NUMBEROFSAMPLES` must match the count of sample names. `ARRAY=1-N` selects the samples to process; stage 02b uses local metadata and supports the configured array concurrency without EDirect serialization. `PROJECT_DIRECTORY/reads/` must exist before configuration. The master and configurator were designed to remain runnable with Python 3.6 on the login node; step 03 loads Python 3.9.5 (or another Python >=3.8 installed by the user).

Run:

```bash
bash ViroXplore-HPC_config.sh
bash ViroXplore-HPC_master.sh --dry-run
```

**RC7 input preflight:** `--dry-run` and a real master invocation both check the
configured `PROJECT_DIRECTORY/reads/` **before any SLURM jobs are submitted**.
For PE, both `SAMPLE_R1.fastq.gz` and `SAMPLE_R2.fastq.gz` must exist and
be nonempty gzip files; for SE, `SAMPLE_R1.fastq.gz` is required.
An SE configuration emits a warning if `SAMPLE_R2.fastq.gz` also exists,
because R2 would otherwise be silently ignored. Inspect the displayed
`Sequencing mode: PE/SE` before submission. This fast check does not
validate full FASTQ integrity or R1/R2 read-name synchronization.
The same existence check is also performed by stage 01 when it starts.

After configuration, exactly five `*_PE_*.sh` or `*_SE_*.sh` analysis scripts will exist directly in the software directory. Template files remain in `templates/`, and helper programs are copied to `PROJECT_DIRECTORY/tools/`. When mode changes, the inactive-mode generated scripts are moved to `.configuration_backups/`.

## 4. Run the pipeline

```bash
bash ViroXplore-HPC_master.sh
squeue -u "$USER"
```

For individual submission (PE example):

```bash
sbatch 01_ViroXplore-HPC_v0.1_PE_qc_trim_hostrm.sh
```

The five ordered steps are `01`, `02a`, `02b`, `03`, and `04`; the master enforces `afterok` dependencies. Do not manually launch multiple dependent stages until the required input files are available.

## 5. Results and monitoring

The current implementation creates these directories in the project:

| Directory | Purpose |
| --- | --- |
| `01_fastqc/` | QC summaries |
| `02_trimmed/` | Trimmed FASTQ files |
| `03_aligned/` | Non-host reads |
| `04_assembly/` | SPAdes assembly; PE filtered `scaffolds_filtered.fasta`, SE filtered `contigs_filtered.fasta` |
| `04b_mapping/` | Viral-reference mapping outputs, tables and plots |
| `05_discovery/` | DIAMOND hit classification, best-hit table and review/exclusion tables |
| `06_remapping/` | Remapping BAM and coverage plots |

Inspect corresponding SLURM standard output/error logs in `PROJECT_DIRECTORY/` and the master submission table `pipeline_runs/submitted_*.tsv`. The configurator validates Bash syntax and script hashes, not database availability or scientific correctness.

The final discovery assembly selection is written as `04_assembly/SAMPLE/finalviralhits.fasta`; this file is subsequently used by step 04. The human-readable table extension `.xls` does **not** imply an Excel binary format; it is tab-separated text. See the files themselves for exact columns.

## 6. Notifications

Set `NOTIFICATION_EMAIL` in the configurator and rerun configuration. The master requests `FAIL` notifications for all stages and an `END` notification for the final stage. Notifications are delivered through the SLURM cluster mail service; if the email is blank, it will use the cluster's configured default if available.

## Troubleshooting

- Python `subprocess.run(..., text=True)` is not supported by Python 3.6. The central configurator/master use Python 3.6-compatible `universal_newlines=True` and `stdout=subprocess.PIPE`/`stderr=subprocess.PIPE`, including validation of Apptainer wrapper scripts.
- If `FASTQ preflight failed` appears, confirm `SEQUENCING_MODE=PE` or `SE` in the central configurator and use the expected `SAMPLE_R1.fastq.gz` and, for PE, `SAMPLE_R2.fastq.gz` filenames. Run `bash ViroXplore-HPC_config.sh` again, then `bash ViroXplore-HPC_master.sh --dry-run`. Do not mistake an R1-only SE run for a PE validation.
- If jobs cannot find `module load`, ensure the cluster module environment is initialized in batch shells.
- If SLURM reports `No partition specified or system default partition`, set `SLURM_PARTITION` in the configurator, reconfigure, and confirm `sinfo -p PARTITIONNAME` shows the partition. Also verify your account is permitted to use it. The master passes the selected partition explicitly.
- If a reference path is wrong, set `REFERENCE_ROOT` to the output directory of the reference installer, re-run the configurator and check that stage 02b and 03 point to existing files.
- If scripts are edited manually after configuration, the master rejects their SHA-256 hashes; re-run the configurator to regenerate scripts from templates.
- An `afterok` chain depends on exit status; check `.err`, `.out`, BAM, FASTA, and result tables independently. The software does not guarantee that every failed internal command will terminate the stage with an error.
