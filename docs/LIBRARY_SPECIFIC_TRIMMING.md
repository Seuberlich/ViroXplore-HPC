# Read trimming settings

## Library-specific read trimming (important)

**Stage 01 is currently configured for the Lexogen CORALL Total RNA library preparations used during ViroXplore-HPC development and validation.** The `fastp` arguments are **not universal defaults for all sequencing libraries**. Before analysing datasets generated using a different library preparation protocol, inspect and adapt the trimming settings (and any adapter/UMI handling) according to the library manufacturer's instructions and your read QC results. In particular, inappropriate fixed-base clipping can remove biological sequence and change downstream virus-detection sensitivity.

The current stage-01 PE and SE templates use the following options:

```bash
-l 33 -W 4 -M 15 -5 3 -3 3 -f 12 -F 9
```

| Option | Current value | Meaning |
| --- | --- | --- |
| `-l` | `33` | Minimum read length after filtering |
| `-W` | `4` | Sliding-window size for quality cutting |
| `-M` | `15` | Mean quality threshold for window cutting |
| `-5` | enabled | Enable 5′ quality cutting |
| `-3` | enabled | Enable 3′ quality cutting |
| `-f` | `12` | Trim 12 bases from the front of read 1 |
| `-F` | `9` | Trim 9 bases from the front of read 2 in PE; in SE, read 2 is absent |

**Verification note (release blocker):** The command above is reproduced verbatim from the tested templates. The standalone `3` tokens after `-5` and `-3` are not documented numeric arguments to these flags. Before treating the trimming setup as portable or recommending it to other users, verify the actual command-line parsing with the installed fastp version and record the resulting effective settings. This release-documentation update intentionally does not alter the stage-01 commands or claim a new validation. In SE mode there is no read 2, so the effect of `-F 9` also merits review. The bundled commands are not general recommendations for other libraries.

To adapt trimming, edit the `fastp` command in the relevant source template **before running** `ViroXplore-HPC_config.sh`:

- `templates/01_ViroXplore-HPC_v0.1_PE_qc_trim_hostrm.sh.in`
- `templates/01_ViroXplore-HPC_v0.1_SE_qc_trim_hostrm.sh.in`

If the project has already been configured, update the generated stage-01 `.sh` file as well, or regenerate the configuration carefully without overwriting project-specific settings. Record any changed options in the analysis methods and inspect the resulting FastQC/fastp quality reports. For reproducibility, the bundled stage-01 templates are unchanged from the validated release candidate.
