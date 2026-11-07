#!/usr/bin/env bash
# Execute one already-configured stage INSIDE an EXISTING SLURM allocation.
# Called by the RC8+ master via stage-specific wrappers. Never execute long stages
# directly on a login node.
set -Eeuo pipefail
if [[ $# -ne 2 ]]; then
    echo 'Usage (inside an active SLURM allocation): run_stage_apptainer.sh /absolute/path/viroxplore.sif /absolute/path/configured_stage.sh' >&2
    exit 2
fi
if [[ -z "${SLURM_JOB_ID:-}" ]]; then
    echo 'ERROR: Run only within a SLURM job/allocation, not on the login node.' >&2
    exit 2
fi
command -v apptainer >/dev/null 2>&1 || { echo 'ERROR: apptainer unavailable on this node' >&2; exit 1; }
image="$1"; stage="$2"
[[ "$image" = /* && -s "$image" ]] || { echo "ERROR: absent / nonabsolute image: $image" >&2; exit 1; }
[[ "$stage" = /* && -s "$stage" ]] || { echo "ERROR: absent / nonabsolute stage: $stage" >&2; exit 1; }
stage_dir="$(dirname "$stage")"
binds=(--bind "$stage_dir:$stage_dir")
if [[ -d /data ]]; then binds+=(--bind /data:/data); fi
# Do not inherit host Python or R library variables into the reproducible image.
# Preserve the SLURM task IDs and CPU counts needed by the RC7 scripts.
export APPTAINERENV_SLURM_JOB_ID="${SLURM_JOB_ID}"
export APPTAINERENV_SLURM_ARRAY_JOB_ID="${SLURM_ARRAY_JOB_ID:-${SLURM_JOB_ID}}"
export APPTAINERENV_SLURM_ARRAY_TASK_ID="${SLURM_ARRAY_TASK_ID:-1}"
export APPTAINERENV_SLURM_CPUS_PER_TASK="${SLURM_CPUS_PER_TASK:-1}"
export APPTAINERENV_SLURM_NPROCS="${SLURM_NPROCS:-${SLURM_CPUS_PER_TASK:-1}}"
export APPTAINERENV_BASH_ENV=/opt/viroxplore/module_compat.sh
exec apptainer exec --cleanenv "${binds[@]}" "$image" /bin/bash "$stage"
