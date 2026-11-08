# GitHub publication review — v1.0.0

## Source-package audit (2026-11-08)

- PE and SE F17 workflows were reported as successfully executed with the rebuilt v1.0.0 SIF on IBU. Refer to `V1_CONTAINER_PE_SE_VALIDATION.md` for observed counts and caveats.
- The current publicly visible GitHub `main` branch initially contained only nine root-level files; the `container/`, `templates/`, `tools/`, `extras/`, `tests/` and `docs/` folders were absent. This archive restores them; verify branch completeness after upload.
- The default reference root in the offline-metadata SLURM helper is now required as an explicit environment variable, rather than pointing to an institutional project location.
- `README.md` was updated to remove an obsolete claim that the rebuilt SIF had not been PE/SE validated.
- The release-stage scientific scripts and analysis helper algorithms were not changed in this packaging review.
- `fastp` stage-01 argument parsing remains a **release review item**; it is not silently changed by this package.
- Historic internal development notes contain older IBU path examples and RC status statements. They are archived background, not installation defaults; avoid interpreting them as current instructions.
- Full end-to-end database regeneration from fresh NCBI downloads, cross-cluster portability, and legal/source provenance review are not yet fully verified.

**Publication caution:** Review the entire Git history (not just current files) for sensitive content before circulating a public software release.
