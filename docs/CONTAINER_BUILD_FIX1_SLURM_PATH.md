# Container build FIX1: SLURM submission directory

The submitted sbatch script is copied to SLURM's spool directory. `BASH_SOURCE[0]` cannot be used to locate the project's container definition. This release patch resolves the project root from `BUILD_ROOT` (preferred), then `SLURM_SUBMIT_DIR`, and accepts submissions from either the project root or `container/`.

Run from the project root:

```bash
cd /absolute/path/to/ViroXplore-HPC
sbatch --partition=pibu_el8 container/build_apptainer_IBU.sbatch
```

Or explicitly: `sbatch --export=ALL,BUILD_ROOT=/absolute/path/to/ViroXplore-HPC --partition=pibu_el8 /absolute/path/to/ViroXplore-HPC/container/build_apptainer_IBU.sbatch`.

This patch does not change `ViroXplore-HPC.def` or the analytical pipeline. Building the new image and runtime smoke tests still need HPC validation.
