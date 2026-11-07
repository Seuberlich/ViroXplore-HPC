# ViroXplore-HPC v1.0.0 — building the runtime container

The **RC11 FIX3** pipeline was validated with PE and SE input on IBU using an existing Apptainer SIF. This source recipe was built successfully on IBU and its resulting v1.0.0 SIF passed a smoke test and PE/SE execution validation. See [`../docs/V1_CONTAINER_PE_SE_VALIDATION.md`](../docs/V1_CONTAINER_PE_SE_VALIDATION.md). Rebuilding on another system or later date still requires independent verification.

## Build on a SLURM HPC cluster

Prerequisites: Apptainer with permitted `--fakeroot` builds, access to the `mambaorg/micromamba:2.10.0` base image and conda package channels, and sufficient cache/tmp storage on the compute node. Never build a heavy image on a login node.

From the repository directory:

```bash
export BUILD_ROOT="$PWD"
sbatch --partition=YOUR_PARTITION container/build_apptainer_IBU.sbatch
```

The build wrapper finds `container/` under `BUILD_ROOT` (or `SLURM_SUBMIT_DIR`) rather than the spooled SLURM script path and places `viroxplore-hpc_v1.0.0.sif` under `BUILD_ROOT` by default. Set `IMAGE=/absolute/path/file.sif` and `MANIFEST_DIR=/absolute/path/manifest` to override. It refuses to overwrite an existing image unless `FORCE_BUILD=1` is set. Run `sbatch` with a partition appropriate to your cluster; the script intentionally contains no fixed partition.

Outputs in `container_build_manifest/`: image SHA256, original build-input SHA256 values, a resolved Conda package inventory, Python version, and smoke-test output. Record the Apptainer version and the originating OCI image digest separately. An environment with version ranges does **not** guarantee byte-for-byte reproducibility across future conda repository updates.

## Test a newly built image

```bash
apptainer exec --cleanenv ./viroxplore-hpc_v1.0.0.sif /bin/bash /opt/viroxplore/smoke_test.sh
```

This checks executable availability and the R `readr` and Python `sqlite3` dependencies. The mapping stage is offline and does not need `epost`, `esummary`, `efetch` or `xtract`; they have been removed from the smoke-test requirements. A smoke-test pass does **not** prove successful PE and SE execution. Validate both modes on a small controlled dataset and compare their reports with the validated RC11 FIX3 outputs before publishing this newly built image.

## Alternative Docker build

From `container/`:

```bash
docker build -t viroxplore-hpc:1.0.0-rc .
docker run --rm viroxplore-hpc:1.0.0-rc /bin/bash /opt/viroxplore/smoke_test.sh
```

## Operational notes

Data, STAR indices, RefSeq FASTA/Bowtie2 references, SQLite metadata, DIAMOND nr and all results remain **external** to the container. Configure and mount/bind their real paths; see the root README and installation documentation. `run_stage_apptainer.sh` is intended to be invoked inside a SLURM allocation, not on the login node. Module calls in original analysis scripts are handled by `module_compat.sh` inside the image.

NCBI downloads occur during one-time reference creation, **not** during RC11 offline RefSeq mapping. For the DIAMOND database builder, the host job must provide DIAMOND if configured to run outside the SIF.

Historic RC7–RC10 build instructions are development history, not current v1.0.0 instructions. Do not upload a multi-gigabyte `.sif` to the source-code repository.
