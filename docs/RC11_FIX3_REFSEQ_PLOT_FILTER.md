# RC11 FIX3 — RefSeq coverage plot whitelist

The RC11 FIX2 PE validation produced 42 final RefSeq table rows and 45 plots. This
was because `getplots_depths.r` scanned all `.depth` files, while the mapping
script built the filtered accession list `plotting/NEW` but did not pass it to R.

Both `02b_..._PE_mapping.sh.in` and `02b_..._SE_mapping.sh.in` now call
`Rscript "$PLOTTING_SCRIPT" NEW`.

`tools/getplots_depths.r` uses that file as an exact accession whitelist,
producing a `.depth.pdf` only for each selected accession. It fails if the
whitelist names a missing depth table, rather than silently providing an
incomplete plot archive. Standalone R invocations without arguments retain
legacy all-depth behavior.

No changes to mapping/annotation, the 16-column table, the phage filter, or
the Apptainer container were necessary. Configured projects must deploy BOTH
updated mapping script(s) AND `tools/getplots_depths.r`; just replacing the
release archive does not update already-configured directories.

Regression checks: `bash -n` PE and SE, whitelist vs table assertions against
RC11_PE.zip. Full end-to-end HPC validation is still required.
