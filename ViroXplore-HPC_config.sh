#!/usr/bin/env bash
# ViroXplore-HPC: local configuration (tested core unchanged)
####################################################
###### CENTRAL CONFIGURATOR: ALL FIVE STAGES ####
###### Preserve path, array, and quoting conventions ####
####################################################

# Edit the values below for the local HPC environment:
PROJECT_DIRECTORY=/absolute/path/to/my_project
SAMPLE_NAMES='("Sample1")'
HOST_GENOME=/absolute/path/to/STAR_genome_index
NUMBEROFSAMPLES=1
ARRAY=1

# SLURM partition used by all analysis steps and by the master submission.
# Check available partitions with: sinfo -o "%P %a %l %D"
SLURM_PARTITION=pibu_el8

# Reference databases built with extras/database_builder/setup_references.sh.
# The installer uses this shared root for both RefSeq/Bowtie2 and viral-nr/DIAMOND.
REFERENCE_ROOT=/absolute/path/to/reference_databases

# PE or SE; only the selected mode is generated in the pipeline root.
SEQUENCING_MODE=PE

# Execution backend: native (existing HPC modules) or apptainer (containerized software).
# Container mode is submitted through SLURM by the master with the same resources.
EXECUTION_MODE=native
CONTAINER_IMAGE=/absolute/path/to/viroxplore-hpc.sif

# Email recipient for automatic SLURM master notifications.
# Example: NOTIFICATION_EMAIL="user@example.org"
# Leave empty to use the SLURM default email for the submitting user.
NOTIFICATION_EMAIL=""

# --- DO NOT EDIT BELOW THIS LINE ---
# The original unzip/rm/mv commands have been removed deliberately:
# - generate the five scripts for the selected mode only
# - archive scripts from the inactive mode instead of leaving them in the root
# - preserve the source templates under templates/
# - do not extract ZIP archives automatically; copy helpers to PROJECT_DIRECTORY/tools
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null 2>&1 || { echo 'ERROR: python3 not found' >&2; exit 1; }
python3 - "$SCRIPT_DIR" "$PROJECT_DIRECTORY" "$SAMPLE_NAMES" "$HOST_GENOME" "$NUMBEROFSAMPLES" "$ARRAY" "$SEQUENCING_MODE" "$NOTIFICATION_EMAIL" "$REFERENCE_ROOT" "$SLURM_PARTITION" "$EXECUTION_MODE" "$CONTAINER_IMAGE" <<'PYCODE'
import re
import json
import shlex
import hashlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

root, project, sample_expr, host, n_samples, array_raw, mode, email, ref_root, partition, exec_mode, image_path = sys.argv[1:]
root = Path(root)
project_dir = Path(project)

# Fail before writing anything if the configuration is malformed.
if not project.startswith('/') or re.search(r'[\s\x00"\'`$\\;|&<>]', project):
    sys.exit('ERROR: PROJECT_DIRECTORY needs an absolute path without spaces or shell metacharacters')
if not host.startswith('/') or re.search(r'[\s\x00"\'`$\\;|&<>]', host):
    sys.exit('ERROR: HOST_GENOME needs an absolute path without spaces or shell metacharacters')
if not ref_root.startswith('/') or re.search(r'[\s\x00"\'`$\\;|&<>]', ref_root):
    sys.exit('ERROR: REFERENCE_ROOT needs an absolute path without spaces or shell metacharacters')
if not project_dir.is_dir():
    sys.exit(f'ERROR: PROJECT_DIRECTORY does not exist: {project}')
if not (project_dir/'reads').is_dir():
    sys.exit(f'ERROR: reads/ directory missing: {project_dir / "reads"}')
if mode not in ('PE','SE'):
    sys.exit('ERROR: SEQUENCING_MODE must be PE or SE')
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', partition):
    sys.exit('ERROR: SLURM_PARTITION must be a nonempty, single valid SLURM partition name')
if exec_mode not in ('native','apptainer'):
    sys.exit('ERROR: EXECUTION_MODE must be native or apptainer')
if exec_mode == 'apptainer':
    if not image_path.startswith('/') or re.search(r'[\s\x00\"\'`$\\;|&<>]',image_path):
        sys.exit('ERROR: CONTAINER_IMAGE must be an absolute path without whitespace/metacharacters')
    if not Path(image_path).is_file() or Path(image_path).stat().st_size == 0:
        sys.exit(f'ERROR: CONTAINER_IMAGE does not exist or is empty: {image_path}')
    if not (root/'container'/'run_stage_apptainer.sh').is_file():
        sys.exit('ERROR: missing container/run_stage_apptainer.sh')
if email and not re.fullmatch(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}', email):
    sys.exit('ERROR: NOTIFICATION_EMAIL must be empty or a valid simple e-mail address')
if not re.fullmatch(r'\(\s*(?:"[A-Za-z0-9_.-]+"\s*)+\)', sample_expr):
    sys.exit('ERROR: SAMPLE_NAMES must look like ("Sample1" "Sample2"), using simple sample names')
samples = re.findall(r'"([A-Za-z0-9_.-]+)"', sample_expr)
if len(samples) != len(set(samples)):
    sys.exit('ERROR: duplicate SAMPLE_NAMES')
if not n_samples.isdigit() or int(n_samples) != len(samples):
    sys.exit(f'ERROR: NUMBEROFSAMPLES={n_samples!r} differs from sample count {len(samples)}')
if not re.fullmatch(r'[1-9][0-9]*(?:-[1-9][0-9]*)?(?:%[1-9][0-9]*)?', array_raw):
    sys.exit('ERROR: ARRAY must be N or 1-N or 1-N%limit')
base_range = array_raw.split('%', 1)[0]
if '-' in base_range:
    first, last = (int(i) for i in base_range.split('-', 1))
else:
    first, last = 1, int(base_range)
if first != 1 or last < first or last > len(samples):
    sys.exit(f'ERROR: ARRAY must cover 1..N with N <= {len(samples)}')
array = (f'1-{last}' if last != 1 else '1')
limit = array_raw.partition('%')[2]
if limit:
    array += '%' + limit
mapping_array = array  # RC10: offline metadata permits normal array parallelism

all_templates = sorted((root/'templates').glob('*.sh.in'))
if len(all_templates) != 10:
    sys.exit(f'ERROR: expected 10 original PE/SE templates, found {len(all_templates)}')
templates = [p for p in all_templates if f'_{mode}_' in p.name]
inactive = [root/p.name[:-3] for p in all_templates if f'_{mode}_' not in p.name]
if len(templates) != 5 or len(inactive) != 5:
    sys.exit(f'ERROR: expected five scripts per mode, found {len(templates)} for {mode}')
required_helpers = ('getplots2.r', 'getplots_depths.r', 'filter_discovery_hits.py', 'offline_ncbi_metadata.py', 'filter_refseq_phages.py')
for helper in required_helpers:
    if not (root/'tools'/helper).is_file():
        sys.exit(f'ERROR: helper absent in package: {helper}')

staged = []
for template in templates:
    target = root / template.name[:-3]
    txt = template.read_text(encoding='utf-8')
    is_mapping = template.name.startswith('02b_')
    # RC10: 02b performs offline metadata lookups and uses the normal array.
    txt = (txt.replace('PUT_PATH_HERE', project)
              .replace('PUT_SAMPLE_NAMES_HERE', sample_expr)
              .replace('PUT_HOST_GENOME_HERE', host)
              .replace('PUT_REFERENCE_ROOT_HERE', ref_root)
              .replace('PUT_SLURM_PARTITION_HERE', partition)
              .replace('PUT_NUMBEROFSAMPLES_HERE', n_samples)
              .replace('PUT_ARRAY_HERE', array)
              .replace('PUT_MAPPING_ARRAY_HERE', mapping_array))
    if re.search(r'PUT_[A-Z_]+_HERE', txt):
        sys.exit(f'ERROR: unresolved placeholder in {target.name}')
    # Avoid syntactically broken SLURM scripts even before they can be submitted.
    syntax = subprocess.run(['bash', '-n'], input=txt, universal_newlines=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if syntax.returncode:
        sys.exit(f'ERROR: syntax in {target.name}: {syntax.stderr}')
    staged.append((target, txt))

# Generate one SLURM wrapper per stage in container mode. Preserve ALL
# resource/#SBATCH directives from the original tested stage, while running
# its body in Apptainer on the allocated compute node. The wrapper is a
# separate .sbatch file and does not change the scientific stage's checksum.
container_wrappers = []
if exec_mode == 'apptainer':
    for target, script_body in staged:
        directives = [line for line in script_body.splitlines() if line.startswith('#SBATCH ')]
        if not directives:
            sys.exit(f'ERROR: stage {target.name} has no SLURM directives')
        stage_id = target.name.split('_', 1)[0]
        wrapper_name = f'.apptainer_stage_{stage_id}.sbatch'
        wrapper = root / wrapper_name
        wrapper_content = ('#!/usr/bin/env bash\n' + '\n'.join(directives) + '\n'
            + '# Generated by ViroXplore-HPC_config.sh; do not edit.\n'
            + 'set -Eeuo pipefail\n'
            # sbatch spools a COPY of this wrapper into /var/spool/slurmd/job...;
            # BASH_SOURCE[0] would point to the spool copy, not to this repo.
            # Record the configured, absolute pipeline root at generation time.
            + 'HERE=' + shlex.quote(str(root.resolve())) + '\n'
            + 'exec /bin/bash "$HERE/container/run_stage_apptainer.sh" '
            + shlex.quote(image_path) + ' "$HERE/' + target.name + '"\n')
        syntax = subprocess.run(['bash','-n'],input=wrapper_content,universal_newlines=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if syntax.returncode:
            sys.exit(f'ERROR: generated wrapper {wrapper_name} syntax: {syntax.stderr}')
        container_wrappers.append((wrapper,wrapper_content))

# All validation has passed. First prepare safe replacement and cleanup paths.
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = root / '.configuration_backups'

def backup_path(name):
    # Do not keep inactive, executable .sh files in the pipeline's top-level directory.
    backup_dir.mkdir(exist_ok=True)
    candidate = backup_dir / (name + '.bak_' + stamp)
    index = 1
    while candidate.exists():
        candidate = backup_dir / (name + '.bak_' + stamp + '_' + str(index))
        index += 1
    return candidate

def install_text(dest, data):
    if dest.is_symlink():
        sys.exit(f'ERROR: will not replace symlink: {dest}')
    if dest.exists() and dest.read_text(encoding='utf-8') == data:
        return 'unchanged'
    if dest.exists():
        shutil.copy2(str(dest), str(backup_path(dest.name)))
    # Temporary file + atomic rename prevents incomplete executable scripts.
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=str(dest.parent), delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    tmp_path.chmod(0o644 if dest.suffix == '.json' else 0o755)
    tmp_path.replace(dest)
    return 'written'

# Archive only recognizable pipeline scripts that are no longer active.
# This also handles older names such as 02b_v0.4 or 03_v0.3 from earlier ZIPs.
active_names = set(target.name for target, content in staged)
stage_suffixes = {
    '01': 'qc_trim_hostrm', '02a': 'assembly', '02b': 'mapping',
    '03': 'discovery', '04': 'remapping'
}
pipeline_name = re.compile(
    r'^(01|02a|02b|03|04)_[A-Za-z][A-Za-z0-9_-]*_v[0-9.]+_(PE|SE)_([A-Za-z0-9_]+)\.sh$'
)
def is_recognized_stage_script(filename):
    match = pipeline_name.fullmatch(filename)
    return bool(match and stage_suffixes[match.group(1)] == match.group(3))
stale = sorted(p for p in root.glob('*.sh')
               if is_recognized_stage_script(p.name) and p.name not in active_names)
# Move legacy .sh.bak_* files into the dedicated backup folder as well.
legacy_backups = sorted(p for p in root.glob('*.sh.bak_*')
                        if is_recognized_stage_script(p.name.split('.bak_', 1)[0]))
for old_script in stale + legacy_backups:
    if old_script.is_symlink():
        sys.exit(f'ERROR: will not move symlink: {old_script}')
for old_script in stale + legacy_backups:
    backup = backup_path(old_script.name)
    shutil.move(str(old_script), str(backup))
    print(f'  archived  {old_script.name} (inactive or outdated)')

for target, content in staged:
    status = install_text(target, content)
    print(f'  {status:9} {target.name}')
for wrapper, content in container_wrappers:
    status = install_text(wrapper, content)
    print(f'  {status:9} {wrapper.name} (Apptainer SLURM wrapper)')
if exec_mode == 'native':
    for stale_wrapper in root.glob('.apptainer_stage_*.sbatch'):
        if stale_wrapper.is_symlink():
            sys.exit(f'ERROR: symlink wrapper: {stale_wrapper}')
        shutil.move(str(stale_wrapper),str(backup_path(stale_wrapper.name)))

project_tools = project_dir/'tools'
project_tools.mkdir(exist_ok=True)
for name in required_helpers:
    source, dest = root/'tools'/name, project_tools/name
    if dest.is_symlink():
        sys.exit(f'ERROR: helper target is a symlink: {dest}')
    if dest.exists() and source.read_bytes() == dest.read_bytes():
        continue
    # Preserve a backup and upgrade generated helpers for RC9. Otherwise
    # older helper scripts in project/tools may silently defeat RC10 updates.
    if dest.exists():
        shutil.copy2(str(dest), str(backup_path(dest.name)))
    shutil.copy2(source, dest)
    print(f'  helper    {dest}')

# Manifest for the master submitter: ensures that the selected PE/SE
# scripts are exactly those generated by this central configurator.
manifest = {
    'format_version': 4,
    'project_directory': project,
    'reference_root': ref_root,
    'sequencing_mode': mode,
    'sample_names': samples,
    'array': array,
    'mapping_array': mapping_array,
    'notification_email': email,
    'slurm_partition': partition,
    'execution_mode': exec_mode,
    'container_image': image_path if exec_mode == 'apptainer' else '',
    'container_wrappers': {wrapper.name: hashlib.sha256(content.encode('utf-8')).hexdigest()
                            for wrapper, content in container_wrappers},
    'scripts': {target.name: hashlib.sha256(content.encode('utf-8')).hexdigest()
                for target, content in staged},
}
manifest_status = install_text(root/'.pipeline_configuration.json',
                               json.dumps(manifest, indent=2, ensure_ascii=False)+'\n')
print(f'  {manifest_status:9} .pipeline_configuration.json')

print('\nConfiguration complete:')
print('ViroXplore-HPC: configuration complete')
print(f'  Project:   {project}')
print(f'  References:{ref_root}')
print(f'  Samples:   {len(samples)}: {", ".join(samples)}')
print(f'  Mode:      {mode} (ONLY five {mode} analysis scripts in pipeline folder)')
print(f'  E-Mail:    {email or "SLURM default for submitting user"}')
print(f'  Partition: {partition} (also passed explicitly by the master)')
print(f'  Execution: {exec_mode}' + (f' ({image_path})' if exec_mode == 'apptainer' else ''))
print(f'  Array:     {array}; 02b mapping: {mapping_array} (offline metadata)')
print('  Database:  reference files under REFERENCE_ROOT (see docs/REFERENCE_DATABASES.md)')
print(f'  Manual:    cd {root} && sbatch 01_ViroXplore-HPC_v0.1_{mode}_qc_trim_hostrm.sh')
print(f'  Master:    cd {root} && bash ViroXplore-HPC_master.sh --dry-run')
print(f'             bash ViroXplore-HPC_master.sh')
print('  CAUTION: submitting jobs may overwrite existing results for these samples.')
if exec_mode == 'apptainer':
    print('  Container mode: launch via master or generated .apptainer_stage_*.sbatch wrappers.')
    print('  Directly submitting 01_*.sh etc. runs the native HPC-module variant!')
PYCODE
