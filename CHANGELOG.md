## v1.0.0 GitHub publication review (2026-11-08)

- Restored complete source package for repository upload, including nested directories.
- Reconciled outdated container-validation statements in README.
- Removed institution-specific default reference path from offline metadata SLURM wrapper.
- Added docs/GITHUB_RELEASE_REVIEW.md. No changes to analysis templates.

## v1.0.0 — GitHub source release package (2026-11-07; publication pending)

- PE and SE F17 workflow runs successfully completed using newly built v1.0.0 Apptainer image on IBU. See `docs/V1_CONTAINER_PE_SE_VALIDATION.md`.
- Recorded tested image, RefSeq and DIAMOND database SHA256 checksums in `docs/RELEASE_CHECKSUMS.md`.
- Clarified library-dependent `fastp` settings (validated with Lexogen CORALL total RNA data), container-build requirements and pending full reference-database rebuild validation.
- Final current author list: Michel C. Koch and Torsten Seuberlich; historical development records retained below.
- No modifications to scientific stage templates or mapping/discovery algorithms in this packaging pass.

## v1.0.0 release candidate — authorship metadata correction (2026-11-07)

- Updated current software authorship to Michel C. Koch and Torsten Seuberlich in `AUTHORS.md`, `CITATION.cff`, `README.md`, and release documentation. Historical changelog records remain unchanged.
- No analysis scripts, container definition, or pipeline logic changed.

## v1.0.0 release candidate — 2026-11-07

- Based on RC11 FIX3 after reported successful IBU Apptainer PE and SE runs.
- Correct default `CONTAINER_IMAGE` to a portable placeholder; do not embed an IBU internal path.
- Update README and installation instructions with the current RC11 validation status and container configuration.
- Add `docs/RC11_PE_SE_VALIDATION.md` documenting observed outputs, validation scope, and outstanding checks.
- No scientific analysis template, helper, or pipeline algorithm was modified in this release-preparation pass.

## RC10 FIX1 — multi-source primary organism TaxID (2026-11-05)

- Handle composite GenBank entries (e.g. `NC_043404.1`) with multiple source-feature TaxIDs by matching `/organism` to record-level `ORGANISM`; ambiguous cases fail safely.
- Reuse existing downloaded GBFF without re-downloading; offline-only, PE and SE behavior unchanged.
- Regression tests cover correct primary TaxID selection when it is not the first feature and fail-closed ambiguity.
- Requires a full IBU metadata setup rerun for real-world validation.

## RC10 — offline-only RefSeq taxonomy (2026-11-05)

- Replaced stage 02b EDirect network requests with local SQLite accession/TaxID/scientific-name/definition lookup for PE and SE.
- Added one-time matched RefSeq GBFF + local NCBI taxonomy setup script and IBU batch wrapper; existing Bowtie2 and DIAMOND indexes are reused.
- Rejects incomplete GBFF metadata, TaxID gaps, and snapshot mismatch with the indexed RefSeq FASTA.
- Removed the EDirect serial array restriction; preserves ordinary SLURM array concurrency.
- Master preflight requires a nonempty local offline metadata database before submitting stage 01.
- Python 3.6+ stdlib-only lookup; existing Apptainer SIF remains usable without rebuild.
- Tests cover offline synthetic build and lookup, incomplete annotations, mismatch protection, reference setup and existing PE/SE pipeline tests.
- Not yet validated with real full RefSeq GBFF snapshot on IBU; release candidate only.

## v1.0.0 RC9 (2026-11-02) - container validation fixes
- Step 04 now uses fresh job-specific scratch directories; coverage matching uses exact contig IDs and outputs are verified before publishing.
- Step 01 includes FastQC --threads fix, output validation for PE and SE (from RC8 FIX3).
- Step 02b retries interrupted NCBI EDirect calls and fails with an explicit error if accession or TaxID metadata is incomplete.
- RC8 Apptainer wrapper, SLURM spool fix, Python 3.6 compatibility and tested container recipe retained.
- Requires new project output directories for the first RC9 PE/SE validation runs; existing output data is never modified by package creation.

## RC8 – SLURM spool path FIX2 (2026-11-01)

- Fix Apptainer stage wrappers on SLURM compute nodes: generated wrappers now use the configured absolute pipeline root instead of BASH_SOURCE[0] (which resolves to the SLURM spool directory).
- Add integration regression test that executes a copied SLURM wrapper outside the repository.
- Provide a Python-3.6-compatible repair script for existing customized RC8 PE/SE installations.
- Retain the previous Python-3.6 and container improvements.

## RC8 Python 3.6 FIX1 (2026-11-01)

- Fix central configurator and SLURM master to run on login nodes using Python 3.6: replace Python 3.7+ `subprocess.run(capture_output=True, text=True)` with `stdout=subprocess.PIPE`, `stderr=subprocess.PIPE`, and `universal_newlines=True`.
- No changes to analysis stages, scientific logic, Apptainer image, reference files, or resource configuration.
- Reconfigure PE and SE separately after installing this fix.

## RC7 container prototype FIX1 (2026-10-31)
- Fixed missing micromamba YAML during Apptainer %post by moving it outside /tmp.
- Added build-input checks to SLURM wrapper.

## Release candidate RC7 — PE/SE input preflight and mode transparency
- Master validates mode-specific input FASTQs before submitting **any** SLURM jobs. PE requires both `<sample>_R1.fastq.gz` and `<sample>_R2.fastq.gz`; SE requires R1. The check verifies files are nonempty and have a gzip header; it is not a full FASTQ/pair synchronization validation.
- Dry-run and live submissions explicitly display `Sequencing mode: PE/SE`, project, sample count, and checked FASTQ count. SE warns if matching R2 data exist but will not be analysed.
- Stage 01 PE/SE wrappers additionally check their required FASTQ files on the compute node, including when submitted directly with `sbatch`.
- Preserve the RC6 central partition configuration, PE/SE analysis commands, databases, and reference builder unchanged. No claims of real HPC validation of RC7 yet.

## Release candidate RC6 — centrally configurable SLURM partition
- Add `SLURM_PARTITION` to the central configuration file (default `pibu_el8`).
- Generate mode-specific analysis scripts with `#SBATCH --partition` set from the central configuration.
- Have the master explicitly pass `--partition` for all five SLURM submissions and check consistency with the manifest.
- Keep independent stage submission and automated PE/SE selection; no scientific analysis algorithm changes.
- Update manifest format to version 3. Existing deployments must rerun `ViroXplore-HPC_config.sh`.

## Release candidate RC3: consistent ViroXplore-HPC naming

- Rename central entrypoint to `ViroXplore-HPC_config.sh` and master to `ViroXplore-HPC_master.sh`.
- Rename all ten source templates and their generated analysis scripts with the `ViroXplore-HPC` prefix.
- Update the master, configurator and all English documentation to refer to the new names.
- The configurator archives recognized obsolete stage scripts from earlier builds when run.
- No changes to the biological analysis algorithms, input FASTQ conventions or reference-database builder.

## Unreleased: GitHub release candidate v1.0.0, reference-setup revision

- Translate all remaining German comments in the central configurator into English.
- Standardize the executable names, ten PE/SE stage template names, central configurator, master and documentation on `ViroXplore-HPC` while preserving stage numbers and analysis version numbers.
- Introduce `REFERENCE_ROOT` so the existing configurator populates the RefSeq/Bowtie2 and DIAMOND/NCBI taxonomy paths in PE and SE scripts in one pass.
- Add optional `extras/database_builder/setup_references.sh` to reconstruct the complete NCBI nr FASTA from the officially distributed BLAST database, build the viral nr DIAMOND database, verify sequence counts, and safely remove only installer-created full nr intermediates after success.
- Add automatic RefSeq viral nucleotide FASTA download, Bowtie2 index generation, DUST low-complexity BED and >=10-base homopolymer BED; the contamination TaxID list remains optional and empty unless supplied by the user.
- Add offline mock tests for reference setup and PE/SE configuration and retain the previously successful virus-filter classifier test.
- **Validation:** the new database installer and shared-reference path configuration have not yet been tested on the authors' HPC with live NCBI downloads; the original five-stage internal workflow was tested earlier.

# Changelog

## 1.0.0 (cleaned GitHub release candidate; not yet publicly released)

- Prepared the internally validated HPC pipeline for distribution under the public name **ViroXplore-HPC**.
- Documented the five-stage PE/SE workflow, central configuration, SLURM master, external requirements and input databases.
- Preserved the analysis logic of the ten stage templates, the SLURM master and the three remaining helper files from the successful internal release.
- Generalized sample and deployment defaults in the central configurator for the public candidate; these are examples and must be customized before use.
- Added a separate optional database-builder reference with example locations and a placeholder partition.
- Removed the two unneeded `KeepBestLines` utilities and their configurator dependency.
- Added authorship metadata for Michel C. Koch, Kara LD Dawson and Torsten Seuberlich (University of Bern).
- Added `LICENSE` (BSD-3-Clause), `AUTHORS.md` and `CITATION.cff`.
- Generalized reference paths in the four stage-02b/stage-03 templates; no analysis logic was altered.
- Retained source-provenance checks and clearly documented remaining pre-publication tasks.

The scientific analysis algorithms and stage order were not changed in this release-candidate packaging step. The four template files with deployment-specific database paths were changed only at path literals.

- Recorded the complete Division of Neurological Sciences, Vetsuisse Faculty, University of Bern affiliation for all software authors.

## Release candidate RC4 — taxonomy build restart fix
- Preserve exact protein accession.version identifiers in DIAMOND makedb with `--no-parse-seqids`.
- Add targeted tool for inspecting accession collisions in the filtered taxon map.
- No changes to virus discovery analysis algorithms or existing PE/SE workflows.

## Release candidate RC5 — robust DIAMOND command formatting
- Use a single-line `diamond makedb` command with `--no-parse-seqids` and `--threads` to prevent a missing line-continuation backslash from launching `--threads` as a separate shell command.
- No change to alignment, mapping, assembly, filter algorithms, software dependencies or SLURM resource settings.
- Keep complete nr download intermediates until successful final validation; reruns reuse existing filtered FASTA/taxonmap when available.

### Experimental container FIX2 (31 October 2026)
- Resolved source of unsatisfiable Conda pins identified in IBU job 20730611 by updating container-only dependency ranges.
- Record resolved Conda versions and SIF SHA256 after successful build.
- Native RC7 workflow unchanged; container not validated until IBU build and PE/SE reruns succeed.

## RC8 validation candidate (2026-10-31)
- Added execution mode selector: native or Apptainer.
- Added generated SLURM wrappers per stage for container execution, retaining original resource directives.
- Master validates and submits wrappers in Apptainer mode, preserving PE/SE preflight and dependencies.
- Added `docs/RC8_CONTAINER_TEST.md`; original scientific templates unchanged.

## RC8 FIX3 – 2026-11-01
- Repair FastQC `--threads` argument and fail-fast/report validation for PE and SE.
- Avoid parsing existing PDF plots as coverage tables when rerunning stage 04; fail stage 04 if R plotting fails.

## RC10 FIX2 — 2026-11-05

- Offline RefSeq GBFF importer resolves multiple TaxIDs associated with the
  same record-level primary organism only when the local `nodes.dmp`
  independently proves a unique most-specific ancestor/descendant relationship.
- Other unrelated or ambiguous source TaxIDs remain hard errors; no arbitrary
  first/last TaxID selection.
- Regression case for `NC_003309.1` and divergent taxonomic branches.
- No changes to the pipeline runtime, Bowtie2 index, local database schema or
  Apptainer container image.

- Documented that stage-01 fastp settings are specific to Lexogen CORALL Total RNA library preparations and require review/adaptation for other libraries; stage-01 code remains unchanged.
