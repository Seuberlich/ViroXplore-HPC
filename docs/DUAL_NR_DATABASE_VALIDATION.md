# Matched full and viral nr database validation

## Scope

A matched pair of DIAMOND protein databases was built on IBU on 16–19 November 2026 to support experimental competitive specificity filtering for a future ViroXplore-HPC version. This is additional development documentation, not a modification of the v1.0.0 release or its original reference databases.

Both databases were generated from the same reconstructed NCBI nr FASTA and taxonomy inputs, according to the build manifests. The viral subset includes bacteriophages and archaeal viruses at database construction; downstream filtering remains necessary.

## Build and integrity

SLURM job 21439844 completed with exit code 0:0 after 58 h 35 min 39 s (16 CPUs, 96 h time limit; reported maximum RSS 261036836 K). DIAMOND 2.2.5.185, database format 3, was used.

| Metric | Full nr | Viral nr |
|---|---:|---:|
| Protein records | 1,208,075,337 | 12,972,457 |
| Amino acid letters | 453,748,440,404 | 26,316,210,514 |
| Approximate logical file size (GiB) | 586 | 27 |
| SHA256 verification | PASS | PASS |

The input FASTA contained 1,208,075,337 records, of which 12,972,457 were retained in the viral subset. Both DIAMOND sequence counts matched the extraction summary.

The extraction processed 10,545,145,631 accession-to-taxid rows, indexed 66,521,247 viral accessions and identified 293,196 viral TaxIDs among 3,036,781 taxonomy nodes. All 12 taxonomic regression controls passed. The extraction reported 13,382,689 unknown TaxID assignments and zero invalid TaxIDs, conflicting viral TaxIDs and mixed-origin records. These counters describe the implementation and do not establish the absence of mixed-origin proteins or incomplete annotation.

Independent checksum job 21537650 completed with exit code 0:0 in 24 min 13 s. Both databases, reconstructed nr FASTA, protein accession-to-taxid map, nodes.dmp and names.dmp passed verification. The redundant temporary BLAST database was subsequently removed; the reconstructed FASTA was retained.

## SHA256 identifiers

| File | SHA256 |
|---|---|
| full_nr/nr.dmnd | `face419b008044e0fe99e286eb8f15792b9f10d284091b3e27b0c56fca01a625` |
| viral_nr/viral_all_nr.dmnd | `1b4b54c8184ce44dfc3d478296dd22a8bbe857402093ac033e1908423392eab8` |
| reconstructed nr.faa | `13cc24c2433c66dff3ccb64298bd9bf0e22a2bc8f58603fe27250149ab8da431` |
| prot.accession2taxid.FULL.gz | `8a4bd9eafc58c18c3fc223f63b53e7c57b3e5ccdf65542fc516447b5677ef63c` |
| nodes.dmp | `1fb1a5e4b76f58dbd33becf027281f9a9aac1dfca317c009379dbb58013346fd` |
| names.dmp | `62a35460160459ea54a6ed473700d665c9d21acfbfee3dfd77bb3f77f0b889ba` |

Taxonomy inputs were retrieved from the NCBI taxonomy FTP service. These hashes identify local build artifacts and inputs, not a guaranteed immutable upstream release. The databases are not bundled in the repository.

## Taxonomic search smoke test

SLURM job 21538323 executed two BLASTP searches against the full nr database, using five viral protein queries, 16 threads, five targets per query, and output fields qseqid, sseqid, pident, length, bitscore, staxids. Search restrictions were `--taxonlist 10239` and `--taxonlist 2,2157,2759`. Both searches reached the TEST COMPLETE marker. The viral search returned 25 alignments for five queries and the cellular-restricted search returned 20 alignments for four queries (4030.7 s for the latter).

| Query | Best viral-restricted bitscore | Best cellular-restricted bitscore | Difference |
|---|---:|---:|---:|
| UXB85809.1 | 2466 | 2253 | 213 |
| UMM52736.1 | 1044 | 248 | 796 |
| DAL63394.1 | 411 | 405 | 6 |
| MGA1787374.1 | 245 | no reported hit | NA |
| DAN60650.1 | 219 | 130 | 89 |

All five viral queries had exact self-hits in the viral-restricted results. The cellular-restricted results include mixed taxonomic assignments, for example 7TLY_I with TaxIDs 9606;694009;2697049. Thus taxonlist restrictions do not guarantee exclusive taxonomic origin. These raw maximum scores are illustrative, not calibrated specificity decisions or matched-region comparisons. No cellular negative controls were included in this smoke test.

## Development implications and limitations

Future competitive filtering should classify all reported TaxIDs, distinguish exclusively viral and exclusively cellular hits from mixed or unknown assignments, compare homologous query regions in the same translated reading frame, and retain an explicit review category. A missing reported hit must not be interpreted as proof of absence. Candidate reduction is not equivalent to diagnostic specificity. Thresholds require evaluation with positive and negative datasets before being adopted. All original discovery outputs should remain available.

The build, checksum and smoke tests establish basic technical readiness for experimental use, not exhaustive database annotation accuracy or diagnostic validation.
