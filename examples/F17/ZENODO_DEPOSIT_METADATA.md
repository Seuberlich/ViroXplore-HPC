# Suggested metadata for a separate Zenodo **dataset** deposit

**Title:** F17 demonstration sequencing dataset for ViroXplore-HPC: one million paired-end read pairs and derived single-end reads

**Resource type:** Dataset

**Description:** This dataset contains a downsampled subset of 1,000,000 paired-end read pairs (1,000,000 reads each in R1 and R2) from the F17 short-read sequencing data used in Hierweger et al., *Emerging Infectious Diseases* (2021), DOI 10.3201/eid2712.210491. The raw reads have not undergone host-read removal. A derived 2,000,000-read single-end test file was constructed by concatenating R1 and R2 reads; it is not an independently sequenced SE library. The dataset served in the technical development and execution validation of ViroXplore-HPC v1.0.0. The exact downsampling command and random seed are unavailable; individual files are identified by SHA-256 checksums. Files: R1 FASTQ.gz, R2 FASTQ.gz, derived SE FASTQ.gz, readme, checksums, SE-generation script. This is a demonstration dataset, not an independent diagnostic performance benchmark.

**Related identifiers:**
- Is derived from: https://doi.org/10.3201/eid2712.210491
- Is supplemented by / documents use with software: https://doi.org/10.5281/zenodo.24051799
- Code: https://github.com/Seuberlich/ViroXplore-HPC

**Creators / license:** Verify deposit creator names, institutions and chosen dataset license in Zenodo before pressing Publish. Do not automatically assume that the software BSD-3-Clause license applies to sequencing reads.

**Before publication:** Check all three FASTQ files' SHA-256 values against `checksums.sha256`; include readme and generation script. Once Zenodo assigns the new dataset DOI, add it to `examples/F17/README.md` on GitHub. Do not overwrite the existing software DOI.
