#!/usr/bin/env python3
"""Repair an existing configured ViroXplore-HPC RC8 install in place.

Usage (from ViroXplore-HPC_PE or ViroXplore-HPC_SE):
    python3 repair_RC8_SLURM_spool_FIX2.py

Preserves all user settings in ViroXplore-HPC_config.sh; only fixes the
Apptainer wrapper generator and regenerates/validates the five stages.
Works with Python 3.6 and later.
"""
from pathlib import Path
from datetime import datetime
import subprocess
import sys
import shutil

root = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path.cwd().resolve()
cfg = root / 'ViroXplore-HPC_config.sh'
master = root / 'ViroXplore-HPC_master.sh'
if not cfg.is_file() or not master.is_file():
    sys.exit('ERROR: run this patch from the ViroXplore-HPC_PE or ViroXplore-HPC_SE directory.')
old_line = '            + \'HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\\n\''
new_line = '            + \'HERE=\' + shlex.quote(str(root.resolve())) + \'\\n\''
body = cfg.read_text(encoding='utf-8')
if old_line in body:
    backup = root / ('ViroXplore-HPC_config.sh.before_spool_FIX2_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    shutil.copy2(str(cfg), str(backup))
    updated = body.replace(old_line, new_line)
    if updated == body:
        sys.exit('ERROR: expected replacement did not occur')
    cfg.write_text(updated, encoding='utf-8')
    print('PATCHED: configurator now embeds the absolute pipeline directory.')
    print('Backup:', backup)
elif new_line in body:
    print('ALREADY PATCHED: regenerating wrappers and manifest.')
else:
    sys.exit('ERROR: unexpected configurator version. No changes made. Use RC8 FIX2 package instead.')
print('Reconfiguring five stages and regenerating Apptainer wrappers...')
subprocess.run(['bash', str(cfg)], cwd=str(root), check=True)
for stage in ['01', '02a', '02b', '03', '04']:
    wrapper = root / ('.apptainer_stage_' + stage + '.sbatch')
    if wrapper.exists():
        s = wrapper.read_text(encoding='utf-8')
        expected = 'HERE=' + str(root)
        if expected not in s:
            sys.exit('ERROR: {} does not contain absolute pipeline root'.format(wrapper))
        if 'BASH_SOURCE' in s:
            sys.exit('ERROR: spooled-path bug remains in {}'.format(wrapper))
print('Running master dry-run...')
subprocess.run(['bash', str(master), '--dry-run'], cwd=str(root), check=True)
print('SUCCESS: fixed and validated. You can now start the master again.')
