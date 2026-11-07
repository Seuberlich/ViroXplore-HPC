#!/usr/bin/env bash
#SBATCH --job-name=ViroXplore_offline_refseq
#SBATCH --partition=pibu_el8
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=ViroXplore_offline_refseq_%j.out
#SBATCH --error=ViroXplore_offline_refseq_%j.err

# Submit from ViroXplore-HPC repository root:
#   sbatch extras/database_builder/run_offline_refseq_metadata_IBU.sbatch
# REFERENCE_ROOT may be overridden at submission: sbatch --export=ALL,REFERENCE_ROOT=/your/path ...
set -Eeuo pipefail
REFERENCE_ROOT="${REFERENCE_ROOT:-}"
[[ -n "$REFERENCE_ROOT" ]] || { echo "ERROR: Set REFERENCE_ROOT to your reference database directory before submission (e.g. sbatch --export=ALL,REFERENCE_ROOT=/path/to/reference_databases ...)." >&2; exit 2; }
HERE="${VIROXPLORE_HOME:-${SLURM_SUBMIT_DIR:-$PWD}}"
SETUP="$HERE/extras/database_builder/setup_refseq_offline_metadata.sh"
[[ -s "$SETUP" ]] || { echo "ERROR: setup script not found: $SETUP" >&2; exit 1; }
if ! type module >/dev/null 2>&1; then
  if [[ -r /etc/profile.d/modules.sh ]]; then source /etc/profile.d/modules.sh
  elif [[ -r /usr/share/lmod/lmod/init/bash ]]; then source /usr/share/lmod/lmod/init/bash
  fi
fi
if type module >/dev/null 2>&1; then
  module load "${PYTHON_MODULE:-Python/3.9.5-GCCcore-10.3.0}"
fi
command -v python3 >/dev/null || { echo 'ERROR: python3 missing' >&2; exit 1; }
command -v curl >/dev/null || { echo 'ERROR: curl missing' >&2; exit 1; }
export PYTHON=python3
printf 'Reference root: %s\nSetup script: %s\n' "$REFERENCE_ROOT" "$SETUP"
bash "$SETUP" "$REFERENCE_ROOT"
echo 'PASS: RefSeq accession, taxonomy and title metadata available locally for both PE and SE.'
