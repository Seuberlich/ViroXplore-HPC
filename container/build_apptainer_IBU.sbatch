#!/usr/bin/env bash
#SBATCH --job-name=ViroXplore_apptainer_build
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=ViroXplore_apptainer_build_%j.out
#SBATCH --error=ViroXplore_apptainer_build_%j.err
# Select the cluster partition using: sbatch --partition=YOUR_PARTITION ...
set -Eeuo pipefail

# SLURM runs a spooled COPY of this script; BASH_SOURCE points at /var/spool/slurmd.
# Resolve inputs using BUILD_ROOT or SLURM_SUBMIT_DIR, never the spooled script path.
if [[ -n "${CONTAINER_DIR:-}" ]]; then
  CONTAINER_DIR="$(cd "$CONTAINER_DIR" && pwd -P)"
  BUILD_ROOT="${BUILD_ROOT:-$(cd "$CONTAINER_DIR/.." && pwd -P)}"
else
  SUBMIT_ROOT="${BUILD_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
  SUBMIT_ROOT="$(cd "$SUBMIT_ROOT" && pwd -P)"
  if [[ -f "$SUBMIT_ROOT/container/ViroXplore-HPC.def" ]]; then
    BUILD_ROOT="$SUBMIT_ROOT"
    CONTAINER_DIR="$SUBMIT_ROOT/container"
  elif [[ -f "$SUBMIT_ROOT/ViroXplore-HPC.def" ]]; then
    CONTAINER_DIR="$SUBMIT_ROOT"
    BUILD_ROOT="$(cd "$SUBMIT_ROOT/.." && pwd -P)"
  else
    echo "ERROR: cannot locate container/ViroXplore-HPC.def under '$SUBMIT_ROOT'." >&2
    echo "Submit from the ViroXplore-HPC project root or set BUILD_ROOT=/absolute/path/to/ViroXplore-HPC" >&2
    exit 1
  fi
fi
IMAGE="${IMAGE:-$BUILD_ROOT/viroxplore-hpc_v1.0.0.sif}"
MANIFEST_DIR="${MANIFEST_DIR:-$BUILD_ROOT/container_build_manifest}"
for file in ViroXplore-HPC.def environment.yml module_compat.sh smoke_test.sh; do
  [[ -s "$CONTAINER_DIR/$file" ]] || { echo "ERROR: missing $CONTAINER_DIR/$file" >&2; exit 1; }
done
mkdir -p "$BUILD_ROOT" "$MANIFEST_DIR" "$BUILD_ROOT/apptainer_cache" "$BUILD_ROOT/apptainer_tmp"
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-$BUILD_ROOT/apptainer_cache}"
export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-$BUILD_ROOT/apptainer_tmp}"
command -v apptainer >/dev/null || { echo 'ERROR: apptainer unavailable' >&2; exit 1; }
if [[ -e "$IMAGE" && "${FORCE_BUILD:-0}" != 1 ]]; then
  echo "ERROR: image already exists: $IMAGE (set FORCE_BUILD=1 to replace)" >&2; exit 1
fi
args=(--fakeroot)
if [[ "${FORCE_BUILD:-0}" == 1 ]]; then args+=(--force); fi
printf 'Build input: %s\nOutput image: %s\n' "$CONTAINER_DIR" "$IMAGE"
(cd "$CONTAINER_DIR" && apptainer build "${args[@]}" "$IMAGE" ViroXplore-HPC.def)
apptainer exec --cleanenv "$IMAGE" /bin/bash /opt/viroxplore/smoke_test.sh | tee "$MANIFEST_DIR/smoke_test.log"
apptainer exec --cleanenv "$IMAGE" micromamba list -n base > "$MANIFEST_DIR/conda_packages.txt"
apptainer exec --cleanenv "$IMAGE" python3 --version > "$MANIFEST_DIR/python_version.txt" 2>&1
sha256sum "$IMAGE" | tee "$MANIFEST_DIR/image.sha256"
sha256sum "$CONTAINER_DIR"/{ViroXplore-HPC.def,environment.yml,module_compat.sh,smoke_test.sh} > "$MANIFEST_DIR/build_inputs.sha256"
printf 'PASS: new image built and smoke-tested. Full PE/SE validation for THIS image remains required.\n'
