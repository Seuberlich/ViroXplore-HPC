# RC11 FIX2 — Empty contamination list compatibility

## Problem
In both PE and SE RefSeq mapping templates, the final table generation used `NR==FNR` while reading `contam_suppl_table_3.taxids.list` and `prefinal_wboth.tsv`. If the contamination list was present but empty, every `prefinal_wboth.tsv` line was interpreted as belonging to the first file, resulting in an empty `final_wboth.tsv` and a header-only `.xls`.

## Fix
Use `FILENAME == ARGV[1]` to identify the first input file, even when it has zero records. The `kitcontam_asplund2019` column is still explicitly `yes` or `no`, with 16 output columns. PE and SE mapping templates were updated identically. No database or container rebuild is required.

## Verification
Synthetic 15-column input tested against empty and non-empty contamination lists; outputs have 16 columns and retain input rows. `bash -n` validates both mapping templates. Full IBU PE/SE runs have not been revalidated.
