# Software dependencies and module-based execution

The versions below reflect legacy host-module declarations in the shell templates. They are **not** an inventory of packages installed in the newly built Apptainer container; consult the container build manifest for the latter. They are **not claims about the newest upstream releases** or guarantees of compatibility with arbitrary versions.

| Component | Version encoded in scripts | Where used |
| --- | --- | --- |
| FastQC | 0.11.9 | 01 |
| fastp | 0.23.4 | 01 |
| STAR | 2.7.9a | 01 |
| SPAdes | 3.15.3 | 02a |
| SeqKit | 2.6.1 | 02a |
| Bowtie2 | 2.3.4.1 | 02b, 04 |
| SAMtools | 1.13 | 02b, 04 |
| BEDTools | 2.30.0 | 02b, 04 |
| Python sqlite3 (standard library) | Python 3.6+ | 02b offline metadata |
| UCSC-Utils | 448 | 02b, 04 |
| MariaDB module | 10.6.4 | 02b (UCSC dependency), 04 |
| R-bundle-IBU | R 4.2.1 | 02b, 04 |
| Python | 3.9.5 module | 03 (classifier requires Python >=3.8) |
| DIAMOND | 2.2.5 | 03; external viral database |

The R plotting scripts call `library(readr)`; verify that `readr` is provided by the loaded R environment. The stage-03 classifier uses only the Python standard library. The central configurator/master should run with Python 3.6 or newer.

The current `tools/` directory also contains required offline mapping and filtering helpers (e.g. `offline_ncbi_metadata.py` and `filter_refseq_phages.py`). The former `KeepBestLines` utilities are not used or included. See [THIRD_PARTY_CODE.md](THIRD_PARTY_CODE.md).

**Resources reserved by current templates:** 01: 80 GB/24 h; 02a: 250 GB/96 h; 02b: 80 GB/24 h; 03: 200 GB/24 h; 04: 10 GB/12 h. These are SLURM requests/limits from the tested scripts, **not** measured peak memory or performance benchmarks.

**Optional reference database setup:** requires NCBI BLAST+ (`update_blastdb.pl`, `blastdbcmd`, `dustmasker`), `bowtie2-build`, DIAMOND, Python 3.6+, curl, tar, gzip, sha256sum, considerable scratch storage and outbound access to NCBI FTP HTTPS endpoints. The reference installer is not part of the validated five-stage pipeline.
