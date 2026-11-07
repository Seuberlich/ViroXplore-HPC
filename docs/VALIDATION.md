# Validation and reporting

## Verified deployment status

The underlying internal pipeline was successfully executed in the authors' HPC environment with paired-end and single-end sequencing inputs through the dependency-managed SLURM master. The final email notification was also received. This confirms the workflow's execution in that environment.

**Not yet established by the reported test runs:** diagnostic sensitivity or specificity, false discovery rate, comparative accuracy against other virus-discovery workflows, cross-cluster portability, container compatibility or measured resource performance.

## Suggested retrospective evaluation for an MRA software announcement

Test samples with previously independently supported virus detections; where permissions permit, include both PE and SE, taxonomically diverse viruses, varying abundance, and negative/background specimens. Define expected viruses and confirmation criteria *before* analysis. Track detection against the expected-positive reference set; describe whether absence of a known detection reflects insufficient reads, assembly thresholds, or similarity-search limits. Avoid treating unverified negatives as gold-standard virus absence.

Suggested result table: sample accession/code; data type (PE/SE); reads; independently established target virus; stage-02b detection; stage-03 detection; representative BLASTX similarity and alignment; breadth and depth from remapping; wall-clock time; peak RAM; manually reviewed ambiguous hits.

For resource claims, gather SLURM accounting metrics such as:

```bash
sacct -j JOBID --format=JobID,JobName,Elapsed,AllocCPUS,ReqMem,MaxRSS,State
```

Do not add actual clinical or sequencing sample identifiers to a public repository until permissions have been confirmed. Prefer small synthetic inputs or approved publicly archived reads for a reproducible tutorial.
