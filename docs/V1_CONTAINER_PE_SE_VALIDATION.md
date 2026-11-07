# ViroXplore-HPC v1.0.0 — rebuilt Apptainer container validation

**Date:** 2026-11-07  
**Site:** IBU SLURM cluster, University of Bern  
**Modes:** paired-end (PE) and single-end (SE), F17 test inputs  
**Container filename:** `viroxplore-hpc_v1.0.0.sif`  

The Apptainer image built successfully on IBU and passed its executable smoke test. The same newly built image was then used for five-stage PE and SE workflows. The supplied test result archives `F17_PE.zip` and `F17_SE.zip` were examined for tabular and coverage consistency. The PE archive did not include a separate stage-04 SLURM log, so end-to-end status for that stage is supported by the generated coverage outputs rather than a complete set of job logs.

| Check | PE | SE |
| --- | ---: | ---: |
| RefSeq accessions after filtering | 42 | 40 |
| RefSeq accessions removed | 3 | 3 |
| RefSeq coverage PDFs | 42 | 40 |
| RefSeq result columns | 16 | 16 |
| DIAMOND hit rows | 1,529 | 603 |
| DIAMOND excluded hit rows | 379 | 102 |
| Selected contigs | 66 | 29 |
| Contig coverage PDFs | 66 | 29 |
| RefSeq alignment rate | 2.35% | 5.58% |

The counts agree with prior RC11 FIX3 PE/SE runs on the same test inputs. They demonstrate consistency of selected outputs, **not** diagnostic sensitivity/specificity, complete bitwise identity of assemblies, verification of every taxonomic call, or reproducibility on other HPC systems. SPAdes produced nonfatal warnings in the test runs; their biological implications were not independently resolved.

## Image and reference identities

- Image SHA256: `f8a22813dccd215c6f5f3dd5f4db5b3ec7eb0b47da5040d3f3698e898f5b53ea` (from IBU build log; SIF binary not bundled).
- RefSeq FASTA SHA256: `d80d893d30d1ac2c0997757a07e5b56116f6eb4f249841b2c80ad37d345177df`.
- Viral DIAMOND nr SHA256: `2148b809744887534d028848cc3e3a0e512020992abc66cf10c14af6ad3c0fd2`.

Read these as identities of the tested binary/reference snapshots, **not** checksums for files shipped in the source repository. Raw F17 data and large reference databases are not distributed. See [`RELEASE_CHECKSUMS.md`](RELEASE_CHECKSUMS.md).

## Outstanding validation

- New database creation from original NCBI downloads was not retested end-to-end with this release.
- A second installation on an unrelated HPC architecture remains desirable.
- A rights-cleared, redistributable example dataset and independent biological benchmarking remain future work.
- Base OCI image digest / resolved package lock required for bitwise or fully specified rebuild reproducibility.
