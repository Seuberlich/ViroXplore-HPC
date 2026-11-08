# Restart the IBU database-build job after DIAMOND accession collision

This release corrects `Joining accession mapping... Error: Duplicate keys: XVM46135`
by using exact accession.version IDs (`--no-parse-seqids`).

1. Replace only `extras/database_builder/build_viral_nr_all_v2.sh` in the
   existing installation (or update from the full RC4 archive).
2. Do **not** delete or relocate the intermediate FASTA/map files:
   - `<REFERENCE_ROOT>/nr_build_tmp/nr.faa`
   - `<REFERENCE_ROOT>/viral_nr/viral_all_nr.faa`
   - `<REFERENCE_ROOT>/viral_nr/viral_all_nr.accession2taxid.tsv.gz`
   - `<REFERENCE_ROOT>/viral_nr/.viral_all_nr.filter_complete`
3. From the ViroXplore-HPC root, submit:

   ```bash
   sbatch --export=ALL,TASK=nr extras/database_builder/run_reference_setup_IBU.sbatch
   ```

4. In the SLURM `.out` log expect `Completed filtered FASTA and taxon map
   already exist; skipping extraction.` and `--no-parse-seqids` in the build
   step log. After completion, run the `TASK=check` job.

If a second `Duplicate keys` failure occurs, inspect the reported accession
using `inspect_taxid_collision.py` and provide the results for analysis.

No full NCBI nr redownload is needed when the intermediate files are intact.
