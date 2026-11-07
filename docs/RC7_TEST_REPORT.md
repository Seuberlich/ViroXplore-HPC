# RC7 offline validation summary

RC7 adds configuration/mode guards without modifying the scientific discovery
algorithms or the working reference-database builder from RC6.

## Checks passed (offline development environment)

- Bash syntax validated for the master, configurator, all 10 stage templates,
  and reference database setup scripts.
- 12 automated preflight tests passed, including PE (both reads), PE missing R2,
  empty R2, gzip signature, SE with an available R2 warning, a two-sample array,
  PE-to-SE reconfiguration, and a simulated five-job SLURM dependency chain.
- Existing discovery-filter classifier test passed.
- Existing reference-database helpers and mocked reference-download tests passed.

## Not tested here

- Real execution on the University of Bern IBU SLURM cluster with RC7.
- Complete FASTQ decoding, mate synchronization and biological correctness.
- A real PE end-to-end run with both paired reads.

For a real PE test inspect fastp (-i and -I), STAR (two reads),
SPAdes (--pe1-1, --pe1-2), Bowtie2 (-1, -2), and DIAMOND mode PE.
