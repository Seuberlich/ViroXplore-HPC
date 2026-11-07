# Upgrading from the earlier release candidate

This revision standardizes public-facing executable names on **ViroXplore-HPC**.
The analysis algorithms, stage numbering and stage-version identifiers have not changed.

## Recommended approach

1. Preserve your original, previously tested pipeline installation for reproducibility.
2. Extract this release candidate into a **fresh** `ViroXplore-HPC/` directory.
3. Edit `ViroXplore-HPC_config.sh` with the project, reference, sample, mode and email settings.
4. Run:

   ```bash
   bash ViroXplore-HPC_config.sh
   bash ViroXplore-HPC_master.sh --dry-run
   ```

5. To submit all five stages when the required input data are ready:

   ```bash
   bash ViroXplore-HPC_master.sh
   ```

The configurator generates **only five** `.sh` stage files in the package root,
for the currently selected PE or SE mode. Original stage templates are retained
in `templates/`. It also moves any recognized obsolete stage `.sh` files
into `.configuration_backups/` when rerun in an existing installation.

**Do not submit the new master against scripts configured by an older package**:
regenerate the stages and `.pipeline_configuration.json` first. Keep HPC module
versions and reference paths appropriate for your environment.

The updated naming and reference database setup still require a real HPC validation
before the release candidate is considered a fully validated public release.
