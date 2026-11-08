# RC8 FIX3: FastQC and robust coverage plots

Identified in F17_RNA_1Mio PE Apptainer run (jobs 20842372–20842376).

* Stage 01: correct `fastqc -threads` to `fastqc --threads`, write reports directly to `01_fastqc`, check nonempty `.html` and `.zip` reports, and exit on failure. Applied to PE and SE templates.
* Stage 04: stop with non-zero exit code if R plotting fails, and `getplots2.r` no longer tries to read pre-existing `.pdf` images as tabular coverage input when reusing output directories. Only numeric data tables are plotted. The analogous `.depth` plotting helper is hardened as well.
* Stage 02b: EDirect showed curl (56) EOF errors despite HTTP 200 messages. FIX3 does not change NCBI metadata retrieval or certify completeness of taxonomy annotations; inspect accession metadata in output. This should be addressed independently if the problem repeats.
* Existing Apptainer SIF is unchanged. No need to rebuild the image: R scripts and analysis scripts are bind-mounted from the project.

For an existing RC8 installation: place `patch_RC8_FASTQC_PLOTS_FIX3.py` in its `tools/` subdirectory, run `python3 tools/patch_RC8_FASTQC_PLOTS_FIX3.py`, then `bash ViroXplore-HPC_config.sh` and `bash ViroXplore-HPC_master.sh --dry-run`. Regeneration updates the checksum manifest. If restarting the full pipeline, use a clean results directory to avoid mixing old and new outputs. To recover only FastQC reports from a completed PE run, run FastQC directly on original R1/R2 FASTQs with the existing container image and `--outdir` pointing to `01_fastqc`.
