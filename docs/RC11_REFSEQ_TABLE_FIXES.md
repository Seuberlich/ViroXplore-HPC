# RC11 candidate — RefSeq table fixes (PE + SE)

* The two mapping templates retain the RC10 fully offline accession/taxonomy lookup.
* Default `VIROXPLORE_EXCLUDE_PHAGES=1` filters accessions whose **locally stored** scientific name or GenBank definition contains `phage`, `bacteriophage` or `prophage`. Set `VIROXPLORE_EXCLUDE_PHAGES=0` before job submission to disable. This filter affects the result table only, not the Bowtie2 mapping or BAM.
* **Limitation:** naming-based filtering cannot identify every bacterial virus (e.g. a species labelled only `Escherichia virus ...`). Complete phage host classification would require a curated locally available host/lineage dataset. Do not interpret the filtered table as taxonomically exhaustive.
* The two auxiliary `join` commands explicitly supply zero for unmatched masked/homopolymer stats.
* The final table always has a `kitcontam_asplund2019` field (`yes` or `no`), matching the 16-column header; the previous variable-width output caused the apparent extra header.
* Changes apply to both PE and SE. RC10 PE validation is evidence for the baseline only: the modified scripts must be rerun on the cluster, and the SE validation is still pending.


## RC11 FIX1 – helper deployment correction
The central configurator now installs `filter_refseq_phages.py` in `PROJECT_DIRECTORY/tools/` for both PE and SE projects. The missing copy caused `python3: can't open file .../tools/filter_refseq_phages.py` in the RC11 candidate. Mapping algorithms and reference databases are unchanged. Re-run the configurator for the chosen project or manually copy the helper from the package `tools/` folder.
