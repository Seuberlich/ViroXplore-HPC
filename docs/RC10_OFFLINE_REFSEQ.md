# RC10: Offline-only RefSeq accession/taxonomy annotation (stage 02b)

**Scope:** ViroXplore-HPC stage 02b; both PE and SE; native and Apptainer. No online `epost`, `esummary`, `efetch`, or NCBI HTTP calls remain in **the analysis stage**. This is a test candidate until the new lookup is run end-to-end on IBU. Stages 01, 02a, 03 and 04 are not changed by this feature.

## Why database preparation is still required

The existing Bowtie2 RefSeq FASTA/index records sequence identifiers and sequences, not a complete corresponding versioned accession -> TaxID -> scientific name / definition lookup. NCBI's genomic GenBank-flatfile (GBFF) release contains that information. **Data download is performed once during database setup**, not in the analysis. Setup also uses `nodes.dmp` / `names.dmp` to identify descendants of Viruses TaxID 10239.

`viral.1.1.genomic.fna.gz` normally has a corresponding annotation file named `viral.1.genomic.gbff.gz` in NCBI's RefSeq viral release. The setup script derives the GBFF filename from the FASTA release manifest, downloads/validates GBFF as needed, checks every accession.version in the Bowtie2 reference FASTA, and writes a versioned SQLite file. It refuses to publish incomplete or mismatched metadata. The Bowtie2 index and DIAMOND database are **not** rebuilt by this standalone metadata setup.

## IBU cluster: one-time setup on a compute node

From the **RC10** repository root after extracting it on IBU:

```bash
sbatch extras/database_builder/run_offline_refseq_metadata_IBU.sbatch
```

The reference root defaults to the previously tested database path:

```
/data/projects/p2025-0064_small_ruminant_lentivirus/reference_databases
```

For an alternate reference root:

```bash
sbatch --export=ALL,REFERENCE_ROOT=/absolute/path/to/reference_databases \
  extras/database_builder/run_offline_refseq_metadata_IBU.sbatch
```

Check the output in `ViroXplore_offline_refseq_<JOBID>.out/.err`. Expect:

```
PASS: N / N FASTA references have offline metadata; M TaxIDs
Offline metadata DB: <REFERENCE_ROOT>/refseq_viral/refseq_viral_metadata.sqlite
PASS: RefSeq accession, taxonomy and title metadata available locally for both PE and SE.
```

The script downloads genomic GBFF files only when they are not already present. The download has a significant additional storage requirement (one recent `viral.1.genomic.gbff.gz` was hundreds of MB compressed; decompressed input is larger). Taxonomy files are reused if already installed. No live queries are made during virus discovery.

**Critical snapshot condition:** if your prebuilt `refseq_viral.fna` originated from an older RefSeq release than the currently downloadable GBFF, the setup will **fail clearly** with a `snapshot mismatch` message. Do not suppress this safeguard, since mismatched accessions could silently change virus identification. Use matching pinned historic GBFF files (put them under `refseq_viral/downloads/`) or rebuild the RefSeq FASTA/Bowtie2 index and GBFF metadata together from a fixed release. Before rebuilding references, archive the validated RC9 snapshot for scientific comparisons.

## Running RC10

After the metadata job reports success, adjust `PROJECT_DIRECTORY`, `SAMPLE_NAMES`, `HOST_GENOME`, `REFERENCE_ROOT`, `SEQUENCING_MODE` and `EXECUTION_MODE` in `ViroXplore-HPC_config.sh`. The existing Apptainer `.sif` works unchanged: SQLite and Python are already included. Reconfigure the pipeline and check the master:

```bash
bash ViroXplore-HPC_config.sh
bash ViroXplore-HPC_master.sh --dry-run
```

For a real run, use a **fresh project/output directory** and start `bash ViroXplore-HPC_master.sh`. No online taxonomy method is provided. Step 02b reads:

```
<REFERENCE_ROOT>/refseq_viral/refseq_viral_metadata.sqlite
```

and fails closed if an accession, TaxID, or the matching reference checksum is absent.

## Reproducibility and updates

Keep the SQLite metadata, `refseq_viral.fna`, its Bowtie2 index, original GBFF archive(s), `ncbi_taxonomy/nodes.dmp`, `ncbi_taxonomy/names.dmp`, and the reference build manifest together. The database stores the SHA256 of the FASTA, GBFF, nodes and names and construction time. For a new NCBI release, update the full RefSeq set together; do not mix old indices with new annotations. Python 3.6+ standard library (sqlite3) suffices for lookups.

## Validation status

The 2026-11-05 F17 RC9 tests validated the prior online metadata path in both PE/SE Apptainer modes. RC10 offline metadata functionality is implemented and tested using mocked GenBank data, taxonomy trees, missing accession controls, integrity checks, and the PE/SE master preflight. **RC10 has not yet been executed against the complete real viral RefSeq release on IBU.** Its exact mapping table should be compared with RC9 after the first real run (especially scientific names and GenBank definitions).

## FIX1: multiple source TaxIDs in GenBank (2026-11-05)

The first IBU metadata-setup job (21070670) stopped when the GenBank entry
`NC_043404.1` contained two TaxIDs in different `source` features. FIX1 now
uses the record-level `ORGANISM` name and the matching source feature's
`/organism` to select the primary TaxID. It **never** simply picks the first
TaxID, and rejects records for which multiple TaxIDs are still consistent
with the primary organism or none can be confidently matched. The original
RefSeq FASTA, Bowtie2 index and DIAMOND database are not modified.

The previously downloaded `viral.1.genomic.gbff.gz` is automatically reused;
no repeated 434 MB download is necessary. Rerun only the setup job:

```bash
sbatch extras/database_builder/run_offline_refseq_metadata_IBU.sbatch
```

If a later record remains ambiguous, the builder gives its accession and a
clear error; provide the `.out`/`.err` for targeted inspection. Real full-GBFF
IBU testing remains necessary before declaring the builder validated.

### RC10 FIX2: hierarchical source TaxIDs (2026-11-05)

Some NCBI GBFF entries contain multiple source features whose `/organism` matches
record-level `ORGANISM`, but one feature uses a species TaxID while another
uses an isolate/child TaxID. The importer now reads `nodes.dmp` *before* parsing
GBFF and selects the most-specific TaxID only when **every matching candidate
is on a single ancestry chain** in the same NCBI taxonomy snapshot. It logs
that resolution. If candidate TaxIDs diverge, or the local taxonomy cannot
resolve them, the importer fails instead of guessing.

In particular, the observed `NC_003309.1` record with candidate IDs 180504 and
2883940 will be resolved to 2883940 **if** the user's installed `nodes.dmp`
contains the expected ancestor-descendant relationship. This relationship is
verified at run time; no hard-coded accession/TaxID exceptions are used.

No new download, reference index, schema, Apptainer image or configuration is
needed. Overwrite `tools/offline_ncbi_metadata.py`, run
`python3 tests/test_offline_primary_taxid.py`, and resubmit
`extras/database_builder/run_offline_refseq_metadata_IBU.sbatch`.
