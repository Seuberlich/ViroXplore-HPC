#!/usr/bin/env bash
# SLURM Master: submit 01 -> 02a -> 02b -> 03 -> 04 as job-array dependencies.
# No resources are kept occupied while stages wait; the script only submits jobs.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
  cat <<'HELP'
ViroXplore-HPC - SLURM Master

Usage:
  bash ViroXplore-HPC_master.sh --dry-run  # Check config, stages and dependencies
  bash ViroXplore-HPC_master.sh            # Submit all five stages

Precondition: run bash ViroXplore-HPC_config.sh first.
The configured SEQUENCING_MODE (PE or SE) is selected automatically.
The master checks required R1/R2 FASTQ inputs before any submission.
Each stage starts only if every task in the previous SLURM array succeeds.
Master notifications: final stage END,FAIL; stages 01-03 FAIL.
Configure SLURM_PARTITION, EXECUTION_MODE and NOTIFICATION_EMAIL in the central configurator.
If the notification email is empty,
SLURM's default e-mail address for the submitting user is used.
The five scripts can also be submitted individually as before.
HELP
}

case "${1:-}" in
  --help|-h) usage; exit 0 ;;
  --dry-run) [[ $# -eq 1 ]] || { usage >&2; exit 2; }; dry_run=1 ;;
  '') [[ $# -eq 0 ]] || { usage >&2; exit 2; }; dry_run=0 ;;
  *) usage >&2; exit 2 ;;
esac

manifest="$SCRIPT_DIR/.pipeline_configuration.json"
[[ -f "$manifest" ]] || {
  echo "ERROR: configuration manifest absent. Run the central configurator first:" >&2
  echo "  bash ViroXplore-HPC_config.sh" >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || { echo 'ERROR: python3 unavailable' >&2; exit 1; }

# Capture preflight output without losing Python exit status (unlike process substitution).
preflight="$(python3 - "$SCRIPT_DIR" "$manifest" <<'PYCODE'
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

root, manifest_file = map(Path, sys.argv[1:])
try:
    cfg = json.loads(manifest_file.read_text(encoding='utf-8'))
except (OSError, ValueError) as exc:
    sys.exit('ERROR: could not read configuration manifest: '+str(exc))
if cfg.get('format_version') != 4:
    sys.exit('ERROR: unsupported configuration manifest version')
mode = cfg.get('sequencing_mode')
if mode not in ('PE','SE'):
    sys.exit('ERROR: invalid SEQUENCING_MODE in manifest')
partition = cfg.get('slurm_partition', '')
if not isinstance(partition,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', partition):
    sys.exit('ERROR: invalid SLURM_PARTITION in manifest; re-run configurator')
email=cfg.get('notification_email','')
if not isinstance(email,str) or (email and not re.fullmatch(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',email)):
    sys.exit('ERROR: invalid notification_email in configuration manifest')
exec_mode=cfg.get('execution_mode')
if exec_mode not in ('native','apptainer'):
    sys.exit('ERROR: invalid EXECUTION_MODE in manifest')
container_image=cfg.get('container_image','')
if exec_mode == 'apptainer':
    if not isinstance(container_image,str) or not Path(container_image).is_absolute():
        sys.exit('ERROR: invalid CONTAINER_IMAGE in manifest')
    if not Path(container_image).is_file() or not Path(container_image).stat().st_size:
        sys.exit(f'ERROR: container image missing/empty: {container_image}')
    if not (root/'container'/'run_stage_apptainer.sh').is_file():
        sys.exit('ERROR: missing container stage launcher')
# RC10: refuse to submit a costly five-stage run without offline RefSeq metadata.
reference_root = cfg.get('reference_root', '')
if not isinstance(reference_root, str) or not Path(reference_root).is_absolute():
    sys.exit('ERROR: invalid REFERENCE_ROOT in manifest')
offline_db = Path(reference_root) / 'refseq_viral' / 'refseq_viral_metadata.sqlite'
if not offline_db.is_file() or offline_db.stat().st_size == 0:
    sys.exit('ERROR: missing offline RefSeq metadata: {}\n'
             '  Prepare it before submitting analysis: '
             'bash extras/database_builder/setup_refseq_offline_metadata.sh {}'.format(offline_db, reference_root))
if not cfg.get('project_directory') or not cfg.get('sample_names'):
    sys.exit('ERROR: manifest missing project/samples')
project = cfg['project_directory']
samples = cfg['sample_names']
if not isinstance(project, str) or not Path(project).is_absolute():
    sys.exit('ERROR: invalid PROJECT_DIRECTORY in manifest')
if not isinstance(samples, list) or not samples or any(
    not isinstance(sample, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', sample)
    for sample in samples
):
    sys.exit('ERROR: invalid SAMPLE_NAMES in manifest')
# Validate exactly the FASTQs that step 01 uses. This catches a wrong-mode
# configuration before submitting any of the dependency-managed SLURM jobs.
sys.path.insert(0, str(root / 'tools'))
try:
    from preflight_reads import check_inputs
    checked_files, input_warnings = check_inputs(project, samples, mode)
except (ImportError, OSError, ValueError) as exc:
    sys.exit('ERROR: FASTQ preflight failed: {}\n'
             '  Verify PROJECT_DIRECTORY/reads and SEQUENCING_MODE in '
             'ViroXplore-HPC_config.sh, then rerun configuration.'.format(exc))
if not re.fullmatch(r'1(?:-[1-9][0-9]*)?(?:%[1-9][0-9]*)?',str(cfg.get('array',''))):
    sys.exit('ERROR: invalid array in manifest')

stages = [
    ('01', f'01_ViroXplore-HPC_v0.1_{mode}_qc_trim_hostrm.sh'),
    ('02a', f'02a_ViroXplore-HPC_v0.1_{mode}_assembly.sh'),
    ('02b', f'02b_ViroXplore-HPC_v0.5_{mode}_mapping.sh'),
    ('03', f'03_ViroXplore-HPC_v0.4_{mode}_discovery.sh'),
    ('04', f'04_ViroXplore-HPC_v0.1_{mode}_remapping.sh'),
]
checksums = cfg.get('scripts',{})
if not isinstance(checksums,dict) or set(checksums) != set(name for stage, name in stages):
    sys.exit('ERROR: manifest does not match the five selected mode scripts')
for name, expected in checksums.items():
    f = root/name
    if not f.is_file() or f.is_symlink():
        sys.exit(f'ERROR: configured script missing or symlink: {f}')
    body = f.read_bytes()
    if hashlib.sha256(body).hexdigest() != expected:
        sys.exit(f'ERROR: {name} differs from configured template. Re-run configurator.')
    if re.search(rb'PUT_[A-Z_]+_HERE',body):
        sys.exit(f'ERROR: unresolved template markers: {name}')
    syntax = subprocess.run(['bash', '-n', str(f)], universal_newlines=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if syntax.returncode:
        sys.exit(f'ERROR: Bash syntax failure {name}: {syntax.stderr}')
# Opposite mode must not have runnable scripts in the pipeline root.
other_mode = 'SE' if mode == 'PE' else 'PE'
if list(root.glob('*_'+other_mode+'_*.sh')):
    sys.exit('ERROR: inactive-mode scripts found in pipeline root; re-run configurator')
for stage,name in stages:
    body=(root/name).read_text(encoding='utf-8')
    match=re.search(r'^#SBATCH\s+--array=(\S+)',body,re.M)
    desired=cfg['mapping_array'] if stage=='02b' else cfg['array']
    if not match or match.group(1)!=desired:
        sys.exit(f'ERROR: {name} has wrong SLURM array (expected {desired})')
    partition_match = re.search(r'^#SBATCH\s+--partition=(\S+)', body, re.M)
    if not partition_match or partition_match.group(1) != partition:
        sys.exit(f'ERROR: {name} has wrong SLURM partition (expected {partition})')
    # A master-managed job must not have custom dependencies in the source.
    if re.search(r'^#SBATCH\s+--dependency',body,re.M):
        sys.exit(f'ERROR: embedded dependency in {name}')
# Validate only the expected wrappers, including their hashes and the
# correspondence with the configured PE/SE source scripts.
wrappers=cfg.get('container_wrappers', {})
if exec_mode == 'apptainer':
    required={f'.apptainer_stage_{stage}.sbatch' for stage,name in stages}
    if not isinstance(wrappers,dict) or set(wrappers) != required:
        sys.exit('ERROR: container wrappers missing in manifest; re-run configurator')
    for name,expected in wrappers.items():
        f=root/name
        if not f.is_file() or f.is_symlink():
            sys.exit(f'ERROR: container SLURM wrapper missing: {f}')
        if hashlib.sha256(f.read_bytes()).hexdigest()!=expected:
            sys.exit(f'ERROR: container SLURM wrapper modified: {name}')
        result=subprocess.run(['bash','-n',str(f)],stdout=subprocess.PIPE, stderr=subprocess.PIPE,universal_newlines=True)
        if result.returncode:
            sys.exit(f'ERROR: wrapper Bash syntax failure {name}: {result.stderr}')
else:
    if wrappers:
        sys.exit('ERROR: native mode has unexpected container wrappers in manifest')
# stdout is machine-readable so bash can parse exact five stages
for stage,name in stages:
    print(f'{stage}\t{name}')
print(f'MAIL\t{email}')
print(f'PARTITION\t{partition}')
print(f'MODE\t{mode}')
print(f'PROJECT\t{project}')
print(f'EXECUTION\t{exec_mode}')
if exec_mode == 'apptainer':
    print(f'IMAGE\t{container_image}')
print(f'INPUTS\t{len(checked_files)}')
print(f'SAMPLES\t{len(samples)}')
for warning in input_warnings:
    print(f'WARNING\t{warning}')
PYCODE
)" || exit 1

stages=()
scripts=()
notification_email=""
slurm_partition=""
sequencing_mode=""
project_directory=""
execution_mode=""
container_image=""
checked_input_count=""
sample_count=""
read_warnings=()
while IFS=$'\t' read -r stage script; do
  if [[ "$stage" == "MAIL" ]]; then notification_email="$script"; continue; fi
  if [[ "$stage" == "PARTITION" ]]; then slurm_partition="$script"; continue; fi
  if [[ "$stage" == "MODE" ]]; then sequencing_mode="$script"; continue; fi
  if [[ "$stage" == "PROJECT" ]]; then project_directory="$script"; continue; fi
  if [[ "$stage" == "EXECUTION" ]]; then execution_mode="$script"; continue; fi
  if [[ "$stage" == "IMAGE" ]]; then container_image="$script"; continue; fi
  if [[ "$stage" == "INPUTS" ]]; then checked_input_count="$script"; continue; fi
  if [[ "$stage" == "SAMPLES" ]]; then sample_count="$script"; continue; fi
  if [[ "$stage" == "WARNING" ]]; then read_warnings+=("$script"); continue; fi
  [[ -n "$stage" && -n "$script" ]] || continue
  stages+=("$stage")
  scripts+=("$script")
done <<< "$preflight"
[[ ${#scripts[@]} -eq 5 && -n "$slurm_partition" && "$sequencing_mode" =~ ^(PE|SE)$ && -n "$project_directory" && "$execution_mode" =~ ^(native|apptainer)$ && "$checked_input_count" =~ ^[0-9]+$ && "$sample_count" =~ ^[0-9]+$ ]] || { echo 'ERROR: preflight returned incomplete configuration' >&2; exit 1; }

echo "ViroXplore-HPC - five-stage pipeline"
echo "  Directory: $SCRIPT_DIR"
echo "  Project: $project_directory"
echo "  Sequencing mode: $sequencing_mode"
echo "  Execution mode: $execution_mode"
if [[ "$execution_mode" == "apptainer" ]]; then echo "  Container image: $container_image"; fi
echo "  FASTQ preflight: $checked_input_count required files checked for $sample_count sample(s)"
echo "  SLURM partition: $slurm_partition"
for warning in "${read_warnings[@]}"; do echo "  WARNING: $warning" >&2; done
for i in "${!scripts[@]}"; do
  printf '  %s: %s\n' "${stages[$i]}" "${scripts[$i]}"
done
echo "  Mail recipient: ${notification_email:-SLURM default address for submitting user}"
echo '  Mail events: stage failures (01/02a/02b/03/04), and completion of 04'

if [[ "$dry_run" -eq 1 ]]; then
  echo 'DRY RUN: valid configuration. No jobs submitted.'
  echo 'Dependencies: 01 -> 02a -> 02b -> 03 -> 04 (afterok, all array tasks)'
  echo 'E-mail notification: FAIL on all stages, END on the final stage 04'
  exit 0
fi

command -v sbatch >/dev/null 2>&1 || { echo 'ERROR: sbatch not available; run on SLURM login node' >&2; exit 1; }
# Register the submission before the first job is launched.
mkdir -p "$SCRIPT_DIR/pipeline_runs"
run_file="$SCRIPT_DIR/pipeline_runs/submitted_$(date +%Y%m%d_%H%M%S)_$$.tsv"
printf 'stage\tscript\tjob_id\tdependency\tmail_type\tmail_user\tpartition\n' > "$run_file"
previous=''
for i in "${!scripts[@]}"; do
  stage="${stages[$i]}"
  script="${scripts[$i]}"
  submit_script="$script"
  if [[ "$execution_mode" == "apptainer" ]]; then
    submit_script=".apptainer_stage_${stage}.sbatch"
  fi
  args=(--parsable "--partition=$slurm_partition")
  # Send one completion notice after final stage 04, and alerts if any
  # upstream stage fails (otherwise afterok would prevent stage 04).
  if [[ "$stage" == "04" ]]; then
    mail_type='END,FAIL'
  else
    mail_type='FAIL'
  fi
  args+=("--mail-type=$mail_type")
  if [[ -n "$notification_email" ]]; then
    args+=("--mail-user=$notification_email")
  fi
  dependency='none'
  if [[ -n "$previous" ]]; then
    dependency="afterok:$previous"
    args+=("--dependency=$dependency")
  fi
  if ! response="$(sbatch "${args[@]}" "$submit_script")"; then
    echo "ERROR: sbatch failed at stage $stage. Earlier stages may already be queued." >&2
    echo "Submitted jobs recorded in: $run_file" >&2
    echo 'To cancel submitted jobs if needed: scancel <job_id> ...' >&2
    exit 1
  fi
  # --parsable emits the numeric job id, optionally followed by ;cluster
  jobid="${response%%;*}"
  if [[ ! "$jobid" =~ ^[0-9]+$ ]]; then
    echo "ERROR: sbatch returned unexpected job ID: $response" >&2
    echo "Examine queued jobs with: squeue -u \$USER" >&2
    exit 1
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$stage" "$submit_script" "$jobid" "$dependency" "$mail_type" "${notification_email:-SLURM_DEFAULT}" "$slurm_partition" >> "$run_file"
  printf '  submitted %-3s  job %-12s dependency: %s\n' "$stage" "$jobid" "$dependency"
  previous="$jobid"
done

echo 'All five stages submitted. Later stages are queued, not running yet.'
echo "Submission log: $run_file"
echo "Status: squeue -u \$USER"
echo 'If a stage fails, later stages cannot start with afterok dependencies.'
if [[ "$execution_mode" == "apptainer" ]]; then echo 'Apptainer mode: all five SLURM scripts run inside the container image.'; fi
echo 'E-mail: SLURM sends END on stage 04 success and FAIL on any stage failure.'
echo 'E-mail delivery requires the HPC SLURM mail service to be configured.'
echo 'Note: afterok checks the SLURM exit status; underlying scripts must report failures with nonzero exit status.'
