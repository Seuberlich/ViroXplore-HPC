#!/usr/bin/env bash
#SBATCH --job-name=ViroXplore_refs
#SBATCH --partition=pibu_el8
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=96:00:00
#SBATCH --output=ViroXplore_refs_%j.out
#SBATCH --error=ViroXplore_refs_%j.err

# ViroXplore-HPC: IBU cluster reference database batch wrapper.
# The analytical pipeline is NOT modified by this wrapper.
#
# Submit from the ViroXplore-HPC repository root:
#   sbatch --export=ALL,TASK=refseq extras/database_builder/run_reference_setup_IBU.sbatch
#   sbatch --export=ALL,TASK=nr     extras/database_builder/run_reference_setup_IBU.sbatch
#   sbatch --export=ALL,TASK=all    extras/database_builder/run_reference_setup_IBU.sbatch
#   sbatch --export=ALL,TASK=check  extras/database_builder/run_reference_setup_IBU.sbatch
#
# TASK=refseq by default (safe first test). NR_LOCAL_FASTA may point to an
# existing nr.faa; the setup will NEVER delete user-supplied nr FASTA files.
# The huge temporary full nr.faa and BLAST volumes created by the setup are
# removed only AFTER its viral DIAMOND database passes validation.

set -Eeuo pipefail

ROOT="${REFERENCE_ROOT:?Set REFERENCE_ROOT to your absolute reference database directory}"
TASK="${1:-${TASK:-refseq}}"
case "$TASK" in refseq|nr|all|check|verify-offline) ;; *) echo "ERROR: Unknown TASK '$TASK'. Use refseq, nr, all, check, or verify-offline." >&2; exit 2 ;; esac

say() { printf '[%s] ViroXplore-HPC IBU: %s\n' "$(date '+%F %T')" "$*"; }
trap 'rc=$?; echo "ERROR: IBU reference setup failed at line ${LINENO}, exit code ${rc}" >&2' ERR

# On compute nodes SLURM may execute a temporary copy of this script in a
# spool directory. Therefore DO NOT locate setup_references.sh relative to
# BASH_SOURCE: use SLURM_SUBMIT_DIR (or a user-specified VIROXPLORE_HOME).
SUBMIT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"
SETUP=""
if [[ -n "${VIROXPLORE_HOME:-}" && -f "$VIROXPLORE_HOME/extras/database_builder/setup_references.sh" ]]; then
    SETUP="$VIROXPLORE_HOME/extras/database_builder/setup_references.sh"
elif [[ -f "$SUBMIT_DIR/extras/database_builder/setup_references.sh" ]]; then
    SETUP="$SUBMIT_DIR/extras/database_builder/setup_references.sh"
elif [[ -f "$SUBMIT_DIR/setup_references.sh" ]]; then
    SETUP="$SUBMIT_DIR/setup_references.sh"
else
    echo "ERROR: setup_references.sh was not found." >&2
    echo "Submit the job FROM the ViroXplore-HPC repository root or set VIROXPLORE_HOME." >&2
    echo "SLURM_SUBMIT_DIR=$SUBMIT_DIR" >&2
    exit 2
fi
SETUP="$(cd "$(dirname "$SETUP")" && pwd -P)/$(basename "$SETUP")"

# Initialize modules if they were not brought into the batch shell.
if ! type module >/dev/null 2>&1; then
    if [[ -r /etc/profile.d/modules.sh ]]; then
        # shellcheck disable=SC1091
        source /etc/profile.d/modules.sh
    elif [[ -r /usr/share/lmod/lmod/init/bash ]]; then
        # shellcheck disable=SC1091
        source /usr/share/lmod/lmod/init/bash
    fi
fi
type module >/dev/null 2>&1 || { echo 'ERROR: HPC Environment Modules are unavailable' >&2; exit 1; }

say "Job: ${SLURM_JOB_ID:-manual}; task: $TASK"
say "Reference directory: $ROOT"
say "Setup script: $SETUP"
say "Resources: CPUs=${SLURM_CPUS_PER_TASK:-8}, requested memory=128G, time limit=96h"

# IBU's historically validated modules. Override individual names with the
# environment variables listed below if the cluster changes its module tree.
PYTHON_MODULE="${PYTHON_MODULE:-Python/3.9.5-GCCcore-10.3.0}"
BLAST_MODULE="${BLAST_MODULE:-BLAST+/2.15.0-gompi-2021a}"
BOWTIE2_MODULE="${BOWTIE2_MODULE:-Bowtie2/2.3.4.1-foss-2021a}"
DIAMOND_MODULE="${DIAMOND_MODULE:-diamond/2.2.5}"

module load "$PYTHON_MODULE"
if [[ "$TASK" == refseq || "$TASK" == nr || "$TASK" == all ]]; then
    module load "$BLAST_MODULE"
fi
if [[ "$TASK" == refseq || "$TASK" == all ]]; then
    module load "$BOWTIE2_MODULE"
fi
if [[ "$TASK" == nr || "$TASK" == all || "$TASK" == check ]]; then
    module load "$DIAMOND_MODULE"
fi

say 'Loaded environment:'
module list 2>&1 || true

for program in python3; do
    command -v "$program" >/dev/null || { echo "ERROR: $program was not found" >&2; exit 1; }
done
if [[ "$TASK" == refseq || "$TASK" == nr || "$TASK" == all ]]; then
    for program in curl gzip tar; do
        command -v "$program" >/dev/null || { echo "ERROR: $program was not found" >&2; exit 1; }
    done
    for program in blastdbcmd update_blastdb.pl dustmasker; do
        command -v "$program" >/dev/null || { echo "ERROR: BLAST+ command not found: $program" >&2; exit 1; }
    done
fi
if [[ "$TASK" == refseq || "$TASK" == all ]]; then
    command -v bowtie2-build >/dev/null || { echo 'ERROR: bowtie2-build unavailable' >&2; exit 1; }
fi
if [[ "$TASK" == nr || "$TASK" == all || "$TASK" == check ]]; then
    command -v diamond >/dev/null || { echo 'ERROR: diamond unavailable' >&2; exit 1; }
    diamond version
fi

mkdir -p "$ROOT"
[[ -w "$ROOT" ]] || { echo "ERROR: Reference directory is not writable: $ROOT" >&2; exit 1; }
say 'Available filesystem capacity (not necessarily the project quota):'
df -h "$ROOT" || true

if [[ "$TASK" == nr || "$TASK" == all ]]; then
    say 'WARNING: rebuilding complete nr requires very large disk space (potentially > 1 TB including intermediates).'
    say 'The job does not remove files supplied through NR_LOCAL_FASTA.'
fi

export THREADS="${SLURM_CPUS_PER_TASK:-8}"
export REFERENCE_ROOT="$ROOT"
say "Starting setup_references.sh $TASK"
bash "$SETUP" "$TASK" "$ROOT"
say "Completed task: $TASK"
say "To inspect results: bash '$SETUP' check '$ROOT' (with DIAMOND loaded)"
