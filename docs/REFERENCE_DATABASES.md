# Reference database installation and reproducibility

## Automated reference setup (optional, new and not yet HPC-validated)

The **five-stage PE/SE pipeline** was previously validated with already prepared references. This separate reference setup is a new feature and needs a full test on the destination HPC. It is not part of the SLURM master submission.

Download and build both reference collections by running a separate HPC batch job on a compute node with network access. Ensure BLAST+ (`update_blastdb.pl`, `blastdbcmd`, `dustmasker`), DIAMOND, Bowtie2 (`bowtie2-build`), Python 3.6+, `curl`, `gzip`, `tar`, and `sha256sum` are on `PATH` (load your cluster-specific modules first). For example, in your cluster's dedicated batch submission script:

```bash
bash extras/database_builder/setup_references.sh all /absolute/path/to/reference_databases
```

Alternatively, run `refseq` and `nr` separately to allow different resource or time limits:

```bash
bash extras/database_builder/setup_references.sh refseq /absolute/path/to/reference_databases
bash extras/database_builder/setup_references.sh nr /absolute/path/to/reference_databases
bash extras/database_builder/setup_references.sh check /absolute/path/to/reference_databases
```

**Before downloading nr, verify HPC quota and disk space.** NCBI nr BLAST volumes, the reconstructed full `nr.faa`, the 25+ GB accession map, and filtered FASTA can coexist temporarily. Several **hundred GB**, potentially more depending on the NCBI release, may be needed. Storage, download time and CPU/RAM use depend on the release. Obtain approval for bulk downloads if local cluster rules require it. Running this tool on a login node is not recommended.

### Why a full nr FASTA is reconstructed

Since April 2024, NCBI has **discontinued direct FTP distribution of the BLAST nr FASTA**. This installer uses the officially documented method: `update_blastdb.pl --decompress nr` and then `blastdbcmd -db nr -entry all -out nr.faa`. It downloads the contemporaneous protein accession-to-TaxID map and taxonomy dump, then invokes `build_viral_nr_all_v2.sh` to obtain a **physically filtered DIAMOND database** whose proteins descend from NCBI Viruses TaxID 10239, including phages and archaeal viruses. It does **not** exclude those viruses at database-building time, because taxonomy filtering occurs after DIAMOND BLASTX in stage 03.

The installer checks `diamond dbinfo` and the extraction summary before deleting the **installer-created** temporary full `nr.faa` and its downloaded BLAST nr volumes. If any build or validation step fails, these files remain. Externally supplied files (`NR_LOCAL_FASTA`) are never deleted. Set `REMOVE_TEMP_NR_AFTER_SUCCESS=0` or `REMOVE_BLAST_SOURCE_AFTER_SUCCESS=0` to preserve intermediates. The extracted nr sequence count is also compared with the DIAMOND database sequence count before cleanup. The filtered viral FASTA and accession mapping are retained to support auditing and restarting the database build. If you already have a complete nr FASTA, use:

```bash
NR_LOCAL_FASTA=/some/existing/nr.faa bash extras/database_builder/setup_references.sh nr /absolute/path/to/reference_databases
```

### Bowtie2 RefSeq Viral and ancillary files

The installer downloads **all `viral.*.genomic.fna.gz` genomic FASTA archives listed in the NCBI RefSeq release/viral directory** (not just one assumed numbered archive). For a selected fixed set of URLs, pass `REFSEQ_FILE_URLS_LIST=/absolute/path/list.txt` (one official HTTPS URL per line). It concatenates the downloads into `refseq_viral.fna` and builds its Bowtie2 index with basename **`refseq_viral.fna`**. It also generates:

- `refseq_viral.fna.masked.bed` from lowercase intervals in the NCBI BLAST+ `dustmasker`-masked FASTA (zero-based BED intervals);
- `refseq_viral.fna.10homopolymers.bed` with runs of 10+ identical A/C/G/T bases (zero-based BED intervals);
- `contam_suppl_table_3.taxids.list`, empty by default. An **empty file means no contamination TaxID flags will be applied**. To use a study-approved list, set `CONTAMINATION_TAXIDS_FILE=/absolute/path/to/list` before running `refseq`.

The DUST-derived BED definition may **not be identical** to the separately prepared `.masked.bed` used in the original internal run. Therefore this new setup does not imply bit-for-bit identical mapping results; validate against your prior data.

RC10 stage 02b uses a **fully offline SQLite accession/TaxID/organism metadata database** generated from the matching RefSeq viral GBFF archive(s) and local NCBI taxonomy files. See `docs/RC10_OFFLINE_REFSEQ.md` for a one-time setup on an existing indexed reference. An existing database will change over time as NCBI releases change; save the generated `build_manifest.txt`, `refseq_files.txt` and `diamond_dbinfo.txt` and record the download date. For precise reproducibility, keep a fixed snapshot of the reference FASTA, taxonomy, source accession set, script version and checksums rather than rebuilding later from updated NCBI sources.

### Directory layout

```text
REFERENCE_ROOT/
├── viral_nr/
│   ├── viral_all_nr.dmnd
│   ├── viral_all_nr.faa
│   ├── viral_all_nr.accession2taxid.tsv.gz
│   ├── viral_all_nr.filter_summary.json
│   ├── build_manifest.txt
│   └── diamond_dbinfo.txt
├── ncbi_taxonomy/
│   ├── nodes.dmp
│   └── names.dmp
├── refseq_viral/
│   ├── refseq_viral.fna
│   ├── refseq_viral_metadata.sqlite
│   ├── refseq_viral.fna.*.bt2  (or .bt2l)
│   ├── refseq_viral.fna.masked.bed
│   ├── refseq_viral.fna.10homopolymers.bed
│   ├── contam_suppl_table_3.taxids.list
│   └── build_manifest.txt
└── taxonomy_inputs/
    ├── taxdump.tar.gz
    └── prot.accession2taxid.FULL.gz
```

Set the **same root directory** in the central `ViroXplore-HPC_config.sh`:

```bash
REFERENCE_ROOT=/absolute/path/to/reference_databases
```

The configurator fills stage-02b and stage-03 database paths automatically. The host STAR index is separately specified as `HOST_GENOME`.

### Source links

- NCBI BLAST FASTA retirement notice: https://ncbiinsights.ncbi.nlm.nih.gov/2024/01/25/blast-fasta-unavailable-on-ftp/
- NCBI documented nr reconstruction: https://www.ncbi.nlm.nih.gov/books/NBK569850/
- NCBI RefSeq Viral FTP: https://ftp.ncbi.nlm.nih.gov/refseq/release/viral/
- NCBI accession map: https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/accession2taxid/prot.accession2taxid.FULL.gz
- NCBI taxonomy: https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz

## Previously validated database snapshot

The internal viral-only nr snapshot from October 2026 contained **11,270,367 sequences and 23,161,461,801 amino acids** (approximately 23 GB `.dmnd`). These figures are *not* guaranteed for later builds. The new automated reference setup has **not yet been tested end-to-end with current NCBI downloads**; even with identical commands, subsequent release content may vary.

## Taxonomic review

`tools/filter_discovery_hits.py` retains confidently non-prokaryotic viral hits, excludes recognizable prokaryotic viruses, and separately reports uncertain taxonomy assignments. Phage host inference is imperfect, and the result must be interpreted conservatively.

### Offline consistency verification (v1.0.0 release candidate)

To verify an existing RefSeq installation without rebuilding or downloading:

```bash
bash extras/database_builder/setup_references.sh verify-offline /absolute/path/to/reference_databases
```

The command exits nonzero if any RefSeq index component, required ancillary
file, SQLite integrity check, FASTA checksum, accession annotation or record
count check fails. It requires only Python 3.6+ and the standard library.
The full RefSeq build already calls the matching GBFF/SQLite metadata installer;
this verification is an additional read-only safeguard, **not** evidence of
full end-to-end validation of the current automatic NCBI reference downloader.
