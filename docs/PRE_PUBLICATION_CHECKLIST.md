# Checklist before making ViroXplore-HPC public

**Status:** cleaned GitHub release candidate `v1.0.0`. Authorship and a proposed BSD-3-Clause license have been incorporated based on the information supplied by the project team. The team indicates that separate institutional approval is not required.

- [x] Remove the two unlicensed `KeepBestLines` utility files and references in the central configurator.
- [x] Credit Michel C. Koch and Torsten Seuberlich (Division of Neurological Sciences, Vetsuisse Faculty, University of Bern, Bern, Switzerland) in `AUTHORS.md` and `CITATION.cff`.
- [x] Add the BSD-3-Clause repository license.
- [x] Replace private project-specific reference paths in the distributed analysis templates with clearly marked example paths.
- [ ] Confirm copyright ownership and compatibility of any reused content **in the remaining scripts** (the team reports that institutional publication approval is not needed).
- [ ] Configure local HPC partition, module commands, Bowtie2 index paths, DIAMOND database and NCBI taxonomy paths for each deployment.
- [ ] Validate the new automated RefSeq and nr database setup end-to-end on the target HPC. Compare DUST/10-homopolymer mask and mapping outcomes with prior reference preprocessing.
- [ ] Verify database documentation, source snapshots, masks/indices, and host genome options.
- [ ] Provide rights-cleared example or validation data, and keep any clinical/confidential FASTQ files out of GitHub.
- [x] Run PE and SE with the newly built v1.0.0 SIF on IBU and compare output tables/plots with RC11 FIX3; see [`V1_CONTAINER_PE_SE_VALIDATION.md`](V1_CONTAINER_PE_SE_VALIDATION.md).
- [ ] Have a second HPC user test installation in a different environment, if possible.
- [ ] Create a GitHub repository named `ViroXplore-HPC`, preferably initially private until the outstanding provenance checks are complete.
- [x] Record agreed software-author names and order as Michel C. Koch and Torsten Seuberlich. Manuscript authorship, if applicable, is separate.
- [ ] Publish a `v1.0.0` GitHub release and connect Zenodo **before** publishing the release if automatic archival is desired.
- [ ] Add the real repository URL and Zenodo DOI to `CITATION.cff` and the MRA manuscript; do not use example/placeholder URLs in a citation.

The newly built v1.0.0 container has passed PE and SE execution validation on IBU. This is not a new diagnostic benchmark or independent cross-cluster installation.
