# Restart after `--threads: command not found`

If `diamond makedb` finishes and prints valid sequence/TaxID statistics, but the
SLURM job fails at the next shell line with `--threads: command not found`,
replace `extras/database_builder/build_viral_nr_all_v2.sh` with the copy in
this RC5 package. In RC5 the makedb command is on **one line**, preserving
`--no-parse-seqids` and `--threads` as options of the same command.

Do not remove `nr_build_tmp/`, `viral_nr/`, `taxonomy_inputs/` or
`ncbi_taxonomy/` before retrying. From the repository root on IBU, run:

```bash
bash -n extras/database_builder/build_viral_nr_all_v2.sh
sbatch --export=ALL,TASK=nr extras/database_builder/run_reference_setup_IBU.sbatch
```

The setup may repeat `diamond makedb`, but should reuse the previously
extracted viral FASTA and accession-to-TaxID map if both outputs and the
completion marker remain intact. On success verify with:

```bash
sbatch --export=ALL,TASK=check extras/database_builder/run_reference_setup_IBU.sbatch
```

Do not overwrite existing working data files or mix scripts from multiple
release candidates. The stage 01–04 pipelines are unchanged by this fix.
