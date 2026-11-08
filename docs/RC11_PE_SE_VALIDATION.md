# RC11 FIX3 — IBU PE/SE execution validation summary

## Scope

The RC11 FIX3 Apptainer-backed five-stage SLURM pipeline was run on the IBU cluster with F17 sample test inputs in PE and SE modes. The analysis outputs supplied for review were inspected. This is **workflow execution validation**, not diagnostic sensitivity/specificity validation or cross-cluster portability testing. Raw input datasets are not distributed with this release.

## Observations

| Check | PE | SE |
|---|---:|---:|
| RefSeq accessions after filtering | 42 | 40 |
| RefSeq coverage PDFs | 42 | 40 |
| RefSeq accessions excluded | 3 | 3 |
| Final RefSeq table columns | 16 | 16 |
| DIAMOND hit rows | 1,529 | 603 |
| Selected viral contigs | 66 | 29 |
| Contig coverage PDFs | 66 | 29 |

Both runs completed the five-stage workflow. Earlier RC11 fixes addressed a missing helper deployment, an empty contamination list causing zero final rows, and exclusion-inconsistent RefSeq plots. The final report counts are matched in FIX3.

## Limitations and pending release verification

- The database-building pipeline has **not** been established as end-to-end validated on IBU using a fresh reference installation.
- A nonfatal SPAdes warning was observed; this does not by itself establish assembly correctness.
- No diagnostic performance claims (sensitivity, specificity, accuracy) can be derived from these execution tests.
- A reproducible public dataset and measured resource profiling remain future work.
- The final release candidate requires a configuration/dry-run check with real paths on the deployment HPC; no reference databases, clinical reads, or container SIF are bundled.
