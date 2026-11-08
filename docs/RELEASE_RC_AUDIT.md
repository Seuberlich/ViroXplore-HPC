# Release-candidate audit

This package is a **release candidate, not a published GitHub release**.

## Changes from RC11 FIX3

- One user-configurable path in the central configurator replaced with a neutral placeholder.
- README, installation guide and changelog updated.
- Validation and audit documentation added.

## Before public publication

1. Confirm the authors and their agreement to release under BSD-3-Clause; verify provenance and permissions for reused code.
2. Reconfirm container builds from the provided definition and that the resulting SIF passes the smoke test.
3. Validate `extras/database_builder/setup_references.sh` in a clean HPC reference directory, or explicitly mark the builder experimental.
4. Run configuration and master `--dry-run` with actual paths and both PE and SE configurations after installation.
5. Choose and license a public, appropriately anonymized test dataset or a synthetic fixture; include retrieval/checksum instructions.
6. Check public README links, package sizes, no personal or institutional restricted paths/secrets, and fill repository/DOI fields in `CITATION.cff` after publication.
