# Container build verification — v1.0.0 candidate

## Baseline confirmed on IBU

- RC11 FIX3 paired-end and single-end full workflow runs succeeded using an existing SIF. This statement does **not** automatically validate a newly rebuilt v1.0.0 SIF.
- Offline RefSeq: 19,625/19,625 accessions annotated, 15,394 taxonomy records; FASTA SHA256 `d80d893d30d1ac2c0997757a07e5b56116f6eb4f249841b2c80ad37d345177df`.
- DIAMOND v2.2.5 existing database: 12,923,183 sequences and 26,273,651,307 letters; SHA256 `2148b809744887534d028848cc3e3a0e512020992abc66cf10c14af6ad3c0fd2`.

## New v1.0.0 image status (updated 2026-11-07)

- IBU build **completed**, executable smoke test **passed**.
- Image SHA256: `f8a22813dccd215c6f5f3dd5f4db5b3ec7eb0b47da5040d3f3698e898f5b53ea`.
- New-image PE and SE workflows: **successfully executed** on F17 test inputs; selected result counts match RC11 FIX3.
- Detailed image-specific evidence: [V1_CONTAINER_PE_SE_VALIDATION.md](V1_CONTAINER_PE_SE_VALIDATION.md).
- This is not bit-for-bit reproducible container build certification (unpinned base digest / dependency resolution).

## Checklist for cluster validation

1. Submit `sbatch --partition=YOUR_PARTITION container/build_apptainer_IBU.sbatch` from repository root. Set `BUILD_ROOT` if desired.
2. Verify job exit code, smoke-test log and `container_build_manifest` files. Investigate all missing executables; do not remove required tools just to pass.
3. Confirm SHA256 of the newly created SIF and record `apptainer --version`.
4. Configure a fresh PE and SE test project to use the **new image**, and run full workflow tests.
5. Compare essential result counts, reference versions, column integrity, phage filtering and coverage plots with RC11 FIX3 validation reports. Differences require investigation, not automatic acceptance.
6. Only after successful image-specific validation mark this recipe as tested for public release.

## Build limitations

The base OCI tag and version-range Conda dependencies are not sufficient for bitwise reproducibility. A future release can pin the base-image digest and resolved package specifications after the IBU build. RefSeq and DIAMOND database rebuilds are not established merely by verifying existing databases.
