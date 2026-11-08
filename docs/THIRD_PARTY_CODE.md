# Code provenance and external dependencies

The files `tools/KeepBestLines_BlastX.py` and `tools/KeepBestLines_BlastN.py`, which credit Chris Wymant, have been **removed** from this distribution. The current analysis does not call either script. The discovery step uses `tools/filter_discovery_hits.py`; its behavior and test cases are documented in the repository.

No part of the removed utilities is redistributed in this release package. Copies previously installed in a user's existing project `tools/` directory are not modified or deleted by the configurator, to avoid destroying user files. Users may remove such obsolete copies themselves after verifying they are not needed by other analyses.

Before public release, the project maintainers should still check the provenance of the remaining shell, Python and R files and ensure the project holds the rights necessary to license all included code. A BSD-3-Clause license for this repository does **not** cover external executables, scientific reference databases or sequencing datasets.

External programs (FastQC, fastp, STAR, SPAdes, Bowtie2, SAMtools, DIAMOND, NCBI EDirect, UCSC-Utils, R, and their dependencies) must be installed separately under their own respective licenses. No program binaries are redistributed.
