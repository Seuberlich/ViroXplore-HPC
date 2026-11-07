**v1.0.0 source release package (publication pending):** the newly built v1.0.0 Apptainer image was tested on the IBU SLURM cluster with F17 PE and SE inputs. RefSeq annotation and filtered plots were checked. This demonstrates workflow execution in this deployment, not diagnostic performance, cross-cluster portability, or bit-for-bit build reproducibility. See [v1.0.0 image-specific validation](docs/V1_CONTAINER_PE_SE_VALIDATION.md). The complete reference builder has not been validated end-to-end from fresh downloads.

# ViroXplore-HPC

**An HPC-oriented, SLURM-managed workflow for virus discovery from high-throughput sequencing (HTS) data.**

ViroXplore-HPC integrates read quality assessment, trimming and host-read removal, *de novo* assembly, nucleotide-reference mapping, protein similarity searches, taxonomic classification, and remapping/coverage visualization. It supports **paired-end (PE)** and **single-end (SE)** FASTQ data and provides both individual SLURM jobs and a dependency-managed five-stage master submission.

**Software v1.0.0 release package (not yet published; based on RC11 FIX3).** Two software authors are credited in [`AUTHORS.md`](AUTHORS.md) and [`CITATION.cff`](CITATION.cff). The included source code is offered under the [BSD 3-Clause License](LICENSE), subject to the team confirming rights to any reused material in the remaining scripts before making the repository public. The two no-longer-used `KeepBestLines` utilities have been removed.

**Important — library-specific trimming:** The stage-01 `fastp` settings were configured for the Lexogen CORALL Total RNA libraries used in validation. They must be reviewed and, where necessary, adapted for other library preparation protocols before analysis. See [library-specific trimming guidance](docs/LIBRARY_SPECIFIC_TRIMMING.md).

## Pipeline at a glance

| Stage | Function | Main programs |
| --- | --- | --- |
| 01 | Read QC, trimming and host-read removal | FastQC, fastp, STAR |
| 02a | *De novo* assembly | SPAdes, SeqKit |
| 02b | Nucleotide mapping against a viral reference collection | Bowtie2, SAMtools, offline RefSeq SQLite metadata, R |
| 03 | Viral protein search and taxonomy-based hit review | DIAMOND, Python |
| 04 | Remapping of virus-positive contigs and coverage plots | Bowtie2, SAMtools, BEDTools, R |

Stages 02a and 02b both use the non-host reads produced by stage 01; the master nevertheless submits all five stages serially (`01 → 02a → 02b → 03 → 04`). A downstream stage is submitted with SLURM `afterok` dependencies and runs only after successful completion of the preceding job array. **SLURM success is defined by the reported job exit code, so output checks are still important.**

## Requirements

- Linux HPC cluster with SLURM (`sbatch`, `squeue`, `sacct`) and environment modules.
- `bash`, `python3` for the central configuration and master submission; **Python ≥3.8** for the discovery taxonomic filtering code (provided as a module inside stage 03).
- External bioinformatics programs as listed in [`docs/SOFTWARE_REQUIREMENTS.md`](docs/SOFTWARE_REQUIREMENTS.md).
- A prepared STAR host-reference index, plus RefSeq viral Bowtie2 and viral-nr DIAMOND references (either prepared manually or through the new optional [`reference setup`](extras/database_builder/README.md)).
- Sufficient compute, RAM, and filesystem space; one-time GBFF/taxonomy download when preparing the offline RefSeq metadata (no NCBI access during stage 02b).

**The release does not bundle sequence databases, reference genomes, reads, or any patient-derived data.** Some templates still contain site-specific module settings inherited from the internally tested implementation. The SLURM partition is controlled centrally by `SLURM_PARTITION`; update module commands for other clusters; see [`docs/INSTALLATION.md`](docs/INSTALLATION.md).

## Quick start (existing SLURM HPC)

```bash
# 1. Configure for your deployment and choose PE or SE.
nano ViroXplore-HPC_config.sh  # Set REFERENCE_ROOT and SLURM_PARTITION

# 2. Generate exactly five stage scripts for your selected mode.
bash ViroXplore-HPC_config.sh

# 3. Validate configuration and dependent stages without submitting jobs.
bash ViroXplore-HPC_master.sh --dry-run

# 4. Submit the complete pipeline through SLURM.
bash ViroXplore-HPC_master.sh

# 5. Follow progress.
squeue -u "$USER"
```

**RC7 safety check:** Before `--dry-run` succeeds or any job is submitted, the master verifies that the required per-sample gzipped FASTQs exist and are nonempty (R1+R2 for PE, R1 for SE), and visibly reports the selected mode. It warns when an SE analysis would ignore a present R2 file. Stage 01 repeats the existence check during execution. These checks do not establish paired FASTQ synchrony or full integrity; see [installation](docs/INSTALLATION.md).

The central configurator expects a project directory containing `reads/`. Set `SLURM_PARTITION` to an accessible partition on your cluster (e.g. `pibu_el8`). It is written into each generated `#SBATCH --partition` directive and passed explicitly by the master to `sbatch --partition`, so manual and master submissions use the same partition. With `SEQUENCING_MODE=PE`, only five PE `.sh` files are generated in the pipeline root (and conversely for SE). The ten `.sh.in` source templates are retained in `templates/`; previously generated scripts of the inactive mode are archived to `.configuration_backups/`.

You can also submit any configured stage with `sbatch <stage_script.sh>`, provided its upstream inputs already exist. The `ViroXplore-HPC_master.sh` script is a **submission script**, not a SLURM job itself, and creates `pipeline_runs/submitted_*.tsv` for tracking. The notification address is controlled by `NOTIFICATION_EMAIL` in the configurator; mail delivery depends on the cluster.

For an existing installation, see [upgrading from RC6](docs/UPGRADING_FROM_RC6.md), [from RC5](docs/UPGRADING_FROM_RC5.md) or [earlier release candidates](docs/UPGRADING_FROM_RC2.md).

See the complete [installation and usage guide](docs/INSTALLATION.md), including FASTQ naming conventions and output paths.

## Reference databases

The stage-03 DIAMOND search uses a **physical viral protein subset of NCBI nr**, constructed using NCBI viral taxonomy (TaxID 10239); **phages and archaeal viruses are retained in the search database** and subsequently assigned to excluded or review categories during taxonomy-based hit filtering. This is intended as a conservative workflow and does **not** constitute verified host-range prediction.

The currently verified IBU DIAMOND database contains **12,923,183 protein sequences and 26,273,651,307 amino acids** (`diamond dbinfo`, version 2.2.5). The exact NCBI download snapshots, taxonomy, filter rules and resulting database content must be recorded to make analyses reproducible. See [reference database documentation](docs/REFERENCE_DATABASES.md). An **optional downloader and reference builder** is included at [`extras/database_builder/setup_references.sh`](extras/database_builder/setup_references.sh). It reconstructs the full nr FASTA from the NCBI BLAST database, extracts its viral subset, builds DIAMOND, and downloads/builds the RefSeq viral Bowtie2 reference and BED masks. It is separate from the five-stage master and has not yet been end-to-end tested on the authors’ HPC. See [reference database documentation](docs/REFERENCE_DATABASES.md).

## Validation status

The rebuilt v1.0.0 Apptainer container has been exercised with PE and SE F17 test inputs on the IBU SLURM cluster; see the [image-specific validation report](docs/V1_CONTAINER_PE_SE_VALIDATION.md). This verifies successful execution in that deployment, **not** sensitivity, specificity, portability across clusters, or performance superiority. See [`docs/VALIDATION.md`](docs/VALIDATION.md) for a template for further retrospective validation with independently characterized datasets.

## Authors, license and citation

**Authors:** Michel C. Koch and Torsten Seuberlich. **Affiliation:** Division of Neurological Sciences, Vetsuisse Faculty, University of Bern, Bern, Switzerland. Full attribution is in [`AUTHORS.md`](AUTHORS.md) and GitHub-readable citation metadata in [`CITATION.cff`](CITATION.cff).

Source code in this repository is licensed under **BSD-3-Clause**; see [`LICENSE`](LICENSE). External software and databases are governed by their own licenses and are not bundled. Two formerly included third-party utilities (`KeepBestLines_BlastN.py` and `KeepBestLines_BlastX.py`) were removed because they are no longer needed; details are in [`docs/THIRD_PARTY_CODE.md`](docs/THIRD_PARTY_CODE.md).

The project team reports that no additional institutional approval is required. Before making the code public, finish the remaining provenance, portability, example-data, and citation tasks listed in [`docs/PRE_PUBLICATION_CHECKLIST.md`](docs/PRE_PUBLICATION_CHECKLIST.md).

**Scope of this release candidate:** the ten analysis templates, SLURM master and surviving analysis helpers retain the tested analysis logic. The central configurator now injects `REFERENCE_ROOT` into nucleotide and protein reference paths; this is a packaging/installation adjustment that requires a new HPC validation. The nr/RefSeq database downloader is newly added and likewise not part of the previously validated compute pipeline. HPC module and SLURM directives may require customization. The previously tested in-house pipeline remains the source of the analysis logic; **ViroXplore-HPC** is its public project name. The renamed stage wrappers should be validated on the target HPC before publication.

### RC11 FIX3 container validation

Both PE and SE were completed on the IBU SLURM cluster in the RC11 FIX3 test series. The PE RefSeq output contained 42 accessions and 42 corresponding coverage PDFs; SE contained 40 accessions and 40 corresponding coverage PDFs. The final tables had 16 tab-separated columns. See [`docs/RC11_PE_SE_VALIDATION.md`](docs/RC11_PE_SE_VALIDATION.md) for the observed results and limitations. Reference database building remains separately unvalidated end-to-end on IBU.

## v1.0.0 container rebuild

For the portable build instructions, smoke test and manifest collection, see [`container/README.md`](container/README.md) and [`docs/CONTAINER_RELEASE_VALIDATION.md`](docs/CONTAINER_RELEASE_VALIDATION.md). The source recipe is prepared for IBU re-testing; a new SIF is **not yet** considered PE/SE-validated.

## v1.0.0 release evidence and limitations

- [PE/SE validation of the newly rebuilt image](docs/V1_CONTAINER_PE_SE_VALIDATION.md); [checksums and reference identifiers](docs/RELEASE_CHECKSUMS.md).
- [Library-specific trimming configuration](docs/LIBRARY_SPECIFIC_TRIMMING.md); bundled stage-01 parameters were used for Lexogen CORALL total RNA libraries and must be adapted to other preparations.
- [Release checklist](docs/PRE_PUBLICATION_CHECKLIST.md). Fresh, fully automated end-to-end database generation, independent deployment, rights-cleared public test data, and a fully locked bitwise-reproducible container build remain open.
