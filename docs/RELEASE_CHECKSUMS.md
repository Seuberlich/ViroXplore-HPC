# Release evidence: tested external binaries and database snapshots

These checksums were obtained on the IBU HPC cluster. **None of these large binaries or databases are included in the source-code ZIP.** Recalculate and verify values before citing them for a separate run.

| Component | SHA256 | Notes |
| --- | --- | --- |
| Apptainer `viroxplore-hpc_v1.0.0.sif` | `f8a22813dccd215c6f5f3dd5f4db5b3ec7eb0b47da5040d3f3698e898f5b53ea` | Successful rebuild and smoke test on IBU; PE/SE tested |
| RefSeq viral FASTA | `d80d893d30d1ac2c0997757a07e5b56116f6eb4f249841b2c80ad37d345177df` | 19,625/19,625 accessions annotated; 15,394 taxonomy records |
| DIAMOND viral nr `.dmnd` | `2148b809744887534d028848cc3e3a0e512020992abc66cf10c14af6ad3c0fd2` | DIAMOND 2.2.5; 12,923,183 sequences; 26,273,651,307 amino acids |

The checks verify existing artifacts; they do not establish a newly downloaded public database will match these snapshots exactly. The repository is distributed without patient-derived reads, private paths, or the binary SIF.
