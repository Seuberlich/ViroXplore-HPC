# Upgrading from ViroXplore-HPC RC5 to RC6

RC6 adds one centrally configured SLURM partition for the five analysis stages.
No biological analysis algorithm, analysis tool, database builder or stage ordering was changed.

## New setting

Edit `ViroXplore-HPC_config.sh`:

```bash
SLURM_PARTITION=pibu_el8
```

Choose a partition available on your cluster (`sinfo -o "%P %a %l %D"`). The partition must support the time and memory requirements of each step.

RC6 writes `#SBATCH --partition=...` into each generated analysis script **and** supplies the same `--partition=...` argument on all five submissions made by `ViroXplore-HPC_master.sh`. Standalone `sbatch STAGE.sh` therefore works without manual partition edits.

## Upgrade an existing installation

1. Back up your edited RC5 configurator and retain your original validated RC5 directory.
2. Extract RC6 into a **new** directory; do not overwrite RC5 source templates.
3. Copy your project, sample, host-reference, `REFERENCE_ROOT`, email and sequencing-mode values to the RC6 central configurator.
4. Set `SLURM_PARTITION` to a valid partition.
5. Run `bash ViroXplore-HPC_config.sh`, then `bash ViroXplore-HPC_master.sh --dry-run`.
6. Submit with `bash ViroXplore-HPC_master.sh` when you intend to start actual jobs.

The central configuration manifest format changes from 2 to 3. Always rerun the **RC6 configurator** before using the **RC6 master**. The master's checksum checks will reject edited or stale generated stage scripts.

**Note:** The optional reference-database setup has its own SLURM file `extras/database_builder/run_reference_setup_IBU.sbatch`. It is not launched by the five-stage analysis master and retains its independent partition setting; override it with `sbatch -p PARTITION ...` or edit its `#SBATCH --partition` line.
