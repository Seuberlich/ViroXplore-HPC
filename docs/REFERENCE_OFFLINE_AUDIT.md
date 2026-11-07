# RefSeq offline metadata integration audit

- `setup_references.sh refseq` and `all` invoke `ensure_refseq_offline_metadata`
  after creating (or recognizing completed) RefSeq FASTA, Bowtie2 index and BED files.
- `setup_refseq_offline_metadata.sh` obtains matching GBFF records and NCBI taxonomy
  during setup (network required unless files already cached), creates
  `refseq_viral_metadata.sqlite`, and verifies the complete FASTA accession set.
- On repeat runs an existing SQLite file is checked against the FASTA SHA256.
- New `verify-offline` is a read-only local validation option to inspect
  already-built databases without downloading, building or running DIAMOND.
- The source pipeline's stage 02b remains unchanged and does not query NCBI.

Limitations: The index file set's presence does not cryptographically prove that
it was built from the same FASTA. Current NCBI downloader and complete nr build
require an independent HPC integration test; prior success of predecessor scripts
is not equivalent to validation of this wrapper.
