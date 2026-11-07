#!/usr/bin/env python3
"""Check mode-specific FASTQ inputs before SLURM jobs are submitted.

This performs a fast presence/size/gzip-signature check, not a complete
FASTQ integrity or paired-read synchronisation check.
"""
from pathlib import Path


def check_inputs(project_directory, samples, mode):
    """Return (checked_files, warnings); raise ValueError on missing inputs."""
    if mode not in ("PE", "SE"):
        raise ValueError("Unsupported sequencing mode: {}".format(mode))
    reads = Path(project_directory) / "reads"
    if not reads.is_dir():
        raise ValueError("Missing FASTQ directory: {}".format(reads))
    checked = []
    warnings = []
    for sample in samples:
        if not sample or '/' in sample or '\\' in sample or sample in ('.', '..'):
            raise ValueError("Invalid sample name: {!r}".format(sample))
        required = ("R1", "R2") if mode == "PE" else ("R1",)
        for mate in required:
            path = reads / (sample + "_" + mate + ".fastq.gz")
            if not path.is_file():
                raise ValueError("{} sample {!r}: required {} FASTQ missing: {}".format(
                    mode, sample, mate, path))
            if path.stat().st_size == 0:
                raise ValueError("{} sample {!r}: {} FASTQ is empty: {}".format(
                    mode, sample, mate, path))
            try:
                with path.open('rb') as stream:
                    signature = stream.read(2)
            except OSError as exc:
                raise ValueError("Cannot open {}: {}".format(path, exc))
            if signature != b'\x1f\x8b':
                raise ValueError("{} sample {!r}: {} lacks gzip header: {}".format(
                    mode, sample, mate, path))
            checked.append(str(path))
        if mode == "SE":
            other = reads / (sample + "_R2.fastq.gz")
            if other.is_file():
                warnings.append("SE sample {!r}: {} exists but will NOT be analysed. "
                                "Choose SE only if R1-only processing is intentional; "
                                "otherwise set SEQUENCING_MODE=PE and reconfigure.".format(sample, other))
    return checked, warnings
