# Cross-HPC validation of ViroXplore-HPC v1.0.0

## Scope and methods

The public F17 metatranscriptomic dataset ([Zenodo DOI 10.5281/zenodo.24083933](https://doi.org/10.5281/zenodo.24083933)) was processed on IBU and UBELIX, two SLURM-managed HPC systems at the University of Bern, in paired-end (PE) and single-end (SE) modes. Each input comprised two million individual reads (one million read pairs in PE mode). The UBELIX downloads matched the published MD5 checksums. All five stages completed with exit code 0:0 in all four runs, as reported in the run records. The UBELIX PE and SE tests were performed on 16 November 2026.

UBELIX used an independently built v1.0.0 Apptainer image and independently prepared references. Local SLURM resource requests, explicit node allocation, SPAdes memory limits and container bind mounts were adapted; the scientific search and hit-filtering parameters were retained. The viral nr snapshots differed between clusters. The independent images are not claimed to be byte-identical.

Eight final tab-delimited result tables were compared. RefSeq accessions include version numbers; TaxIDs were compared as sets. DIAMOND protein identifiers include PDB chain identifiers where present; organism labels were extracted from the terminal brackets of best-hit descriptions. Selected assembled nucleotide sequences were compared by exact string equality after canonicalization against their reverse complements, rather than by local NODE identifiers. Jaccard similarity is intersection size divided by union size.

## Results

| Metric | IBU PE | UBELIX PE | IBU SE | UBELIX SE |
|---|---:|---:|---:|---:|
| Completed workflow stages | 5/5 | 5/5 | 5/5 | 5/5 |
| RefSeq overall alignment rate (%) | 2.35 | 2.33 | 5.58 | 6.06 |
| Retained RefSeq accessions | 42 | 42 | 40 | 40 |
| RefSeq coverage PDFs | 42 | 42 | 40 | 40 |
| RefSeq TaxIDs | 35 | 35 | 34 | 34 |
| DIAMOND hit rows before filtering | 1529 | 1366 | 603 | 281 |
| Excluded DIAMOND hit rows | 379 | 243 | 102 | 42 |
| Selected assembled sequences | 66 | 69 | 29 | 22 |
| Distinct best-hit protein identifiers | 62 | 61 | 25 | 19 |
| Distinct best-hit organism labels | 48 | 48 | 21 | 15 |

| Cross-cluster comparison | PE shared / union | SE shared / union | PE Jaccard | SE Jaccard |
|---|---:|---:|---:|---:|
| RefSeq accessions | 42/42 | 40/40 | 1.000 | 1.000 |
| RefSeq TaxIDs | 35/35 | 34/34 | 1.000 | 1.000 |
| Protein identifiers | 53/70 | 18/26 | 0.757 | 0.692 |
| Organism labels | 42/54 | 14/22 | 0.778 | 0.636 |
| Exact selected nucleotide sequences (orientation-independent) | 46/89 | 17/34 | 0.517 | 0.500 |

All shared selected assembled sequences had identical best-hit protein identifiers. RefSeq rows were identical across clusters for 36/42 PE and 31/40 SE accessions.

### Expected target: Bern perch virus (Actinovirus bernense)

All three segments were recovered in all four runs. All 16 RefSeq columns for these segments were identical between clusters within each mode.

| Segment | RefSeq | PE coverage (%) | SE coverage (%) | PE mean depth | SE mean depth | PE assembled nt | SE assembled nt |
|---|---|---:|---:|---:|---:|---:|---:|
| S | NC_055639.1 | 99.3018 | 99.3018 | 153.691 | 153.301 | 2418 | 2418 |
| M | NC_055638.1 | 99.6845 | 99.7897 | 130.687 | 131.338 | 3792 | 3800 |
| L | NC_055640.1 | 99.6390 | 99.6390 | 36.2414 | 36.7732 | 6349 | 6349 |

All six same-mode cross-cluster target sequence comparisons were exact matches allowing reverse complementation. Best protein hits were YP_010088063.1 (439 aa), YP_010088060.1 (1140 aa), and YP_010088064.1 (2074 aa), each with 100% amino acid identity over the reported alignment in all four runs. Reference coverage is a mapping metric, not a direct measure of assembly completeness.

### UBELIX deployment details

The PE and SE runs used the epyc2 partition and one node per stage. The local resource requests were 48 GiB/2 h for stage 01, 64 GiB/4 h for stage 02a, 32 GiB/4 h for stage 02b, 64 GiB/4 h for stage 03 and 10 GiB/2 h for stage 04. Stage 03 used eight CPUs; the other stages requested one task each. SPAdes used a 56 GB internal memory limit. The local Apptainer launcher explicitly bound the shared scratch project root and disabled conflicting automatic home/site bind mounts. These settings were sufficient for F17 and are not general recommendations for larger datasets.

The host reference was RefSeq assembly GCF_010015445.1, indexed with STAR 2.7.10b and genomeSAindexNbases 13. The UBELIX viral DIAMOND database contained 12,964,443 proteins; the earlier IBU reference contained 12,923,183. PE uses length-filtered scaffolds and SE uses length-filtered contigs (minimum 500 nt).

| Stage | UBELIX PE elapsed | UBELIX SE elapsed |
|---|---:|---:|
| 01 | 00:06:22 | 00:06:13 |
| 02a | 00:21:49 | 00:04:35 |
| 02b | 00:01:17 | 00:00:55 |
| 03 | 00:02:41 | 00:07:14 |
| 04 | 00:01:24 | 00:00:33 |
| Sum (excluding queue waits) | 00:33:33 | 00:19:30 |

SPAdes reported warnings in the UBELIX PE run concerning k-mer coverage estimation and short inferred insert size, but completed and generated the downstream inputs.

## Interpretation and limitations

These results support technical portability in the two tested environments and reproducible recovery of the expected target. They do not establish general diagnostic sensitivity or specificity, bitwise container reproducibility, or exact reproducibility of all discovery candidates. Differences in reference snapshots and upstream processing are confounded. Only selected assemblies, not complete assembly FASTAs, were compared. Organism labels are best-hit descriptions, not confirmed species detections. Three PDB-chain best hits were described as antibody chains (7X8Z_L, 6VU2_H, 7Y7M_G); their inclusion warrants further investigation. The comparison does not establish that the taxonomic filter is exhaustive. The validation uses a single positive dataset and should not be extrapolated to other specimen types or viruses.
