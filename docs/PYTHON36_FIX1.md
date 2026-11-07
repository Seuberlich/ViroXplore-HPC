# RC8 Python 3.6 compatibility fix

If `bash ViroXplore-HPC_config.sh` fails with `TypeError: __init__() got an unexpected keyword argument 'capture_output'` on an HPC login node running Python 3.6, use the corrected RC8 FIX1 package.

The configurator and master both require Python 3.6-compatible subprocess options. Only two files were patched. Both modes (PE/SE) and execution modes (native/Apptainer) are supported.

Extract the package to a new directory (recommended), transfer your existing local settings into `ViroXplore-HPC_config.sh`, then run:

```bash
bash ViroXplore-HPC_config.sh
bash ViroXplore-HPC_master.sh --dry-run
```

Existing installations: replace only `ViroXplore-HPC_config.sh` and `ViroXplore-HPC_master.sh` in both `ViroXplore-HPC_PE` and `ViroXplore-HPC_SE` directories, preserving customized settings in the old configurator. Alternatively patch both in-place:

```bash
sed -i -e 's/capture_output=True/stdout=subprocess.PIPE, stderr=subprocess.PIPE/g' -e 's/text=True/universal_newlines=True/g' ViroXplore-HPC_config.sh ViroXplore-HPC_master.sh
```

This is a Python-host compatibility patch, not an update to the `.sif` image.
