# ViroXplore-HPC reference database setup

The optional `setup_references.sh` downloads and builds the **NCBI nr-derived viral DIAMOND** database and the **NCBI RefSeq viral Bowtie2** nucleotide index, plus associated BED and optional contamination files needed by ViroXplore-HPC stages 02b/03.

```bash
# Run in a sufficiently provisioned HPC batch allocation (NOT a login node).
bash extras/database_builder/setup_references.sh all /absolute/path/to/reference_databases
# Or independently:
bash extras/database_builder/setup_references.sh refseq /absolute/path/to/reference_databases
bash extras/database_builder/setup_references.sh nr /absolute/path/to/reference_databases
bash extras/database_builder/setup_references.sh check /absolute/path/to/reference_databases
```

Requires network access, BLAST+, DIAMOND, Bowtie2, Python 3.6+, curl, gzip, tar, sha256sum, and very substantial temporary disk space for full nr. Set `THREADS`, `NR_LOCAL_FASTA`, `REMOVE_BLAST_SOURCE_AFTER_SUCCESS`, `REMOVE_TEMP_NR_AFTER_SUCCESS` and `CONTAMINATION_TAXIDS_FILE`, and optionally `REFSEQ_FILE_URLS_LIST` via the environment as required (see `bash setup_references.sh --help`).

Because NCBI no longer distributes the complete FASTA file for BLAST nr directly, the installer fetches the formatted BLAST nr files and reconstructs `nr.faa` with `blastdbcmd`. The reconstructed `nr.faa` and downloaded BLAST volumes are deleted **only after** the final DIAMOND database passes `diamond dbinfo`; files supplied by a user are never deleted. It is safe to run `check` to inspect reference status without rebuilding.

**Important:** This reference setup is newly written and has not yet been benchmarked on the authors' HPC. Its DUST-based BED masking and optional empty contaminant list may differ from the original reference preprocessing; verify scientific equivalence before relying on results. Full usage and source links: [`../../docs/REFERENCE_DATABASES.md`](../../docs/REFERENCE_DATABASES.md).

`build_viral_nr_all_v2.sh` remains available as a standalone builder for users who already have `nr.faa`, the taxonomy dump and the FULL accession-to-TaxID mapping. The wrapper passes input/output paths to the builder via environment variables.

### Fix for DIAMOND `Error: Duplicate keys: XVM46135` (RC4)

The filtered FASTA and taxon map contain `accession.version` IDs. DIAMOND's
default parser drops suffixes after the final dot. The bundled `makedb` now
uses `--no-parse-seqids` so accessions such as `XVM46135.1` and `XVM46135.2`
remain distinct. Exact tokens in FASTA headers are used to generate the map.

This is a **restart-only** fix: run `TASK=nr` again using the same reference
root. The builder recognizes `.viral_all_nr.filter_complete` and reuses the
previously extracted `viral_all_nr.faa` and taxon map; `setup_references.sh`
reuses the existing complete `nr.faa`. Do not delete them!

For diagnosis, use `python3 extras/database_builder/inspect_taxid_collision.py
/path/to/viral_all_nr.accession2taxid.tsv.gz XVM46135`.

The new command-line option is supported from DIAMOND 2.1.7 onward. An HPC
validation run is still required; if duplicate keys occur **without** version
suffixes, the source accession-to-TaxID map must be deduplicated separately.

### Read-only offline validation (v1.0.0 candidate)

Before rerunning any large downloads, verify the existing RefSeq reference and
its locally built SQLite annotation database:

```bash
bash extras/database_builder/setup_references.sh verify-offline /absolute/reference/root
```

This command performs **no downloads** and does not modify the reference files.
It checks the Bowtie2 index file set, required BED files, SQLite integrity,
the recorded FASTA SHA256 checksum, every FASTA accession's taxonomic
annotation, and the stored record count. It requires only Python 3.6+ with its
standard library. It does not independently prove that a pre-existing Bowtie2
index was originally generated from this FASTA; validating that requires an
index build manifest or a rebuilt index. The original `check` command remains
a quick presence/status report.

For a fresh build, `setup_references.sh refseq` already invokes
`setup_refseq_offline_metadata.sh` automatically. The first download/build still
requires internet access on the compute node; **analysis does not**.
