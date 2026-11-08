#!/usr/bin/env bash
# Loaded as BASH_ENV only inside the container. Original SLURM scripts use
# `module load` / `module unload` for HPC software, already on container PATH.
# Explicitly reject unexpected module actions instead of silently ignoring them.
module() {
    case "${1:-}" in
        load|unload|purge|list) return 0 ;;
        *) printf 'ERROR: unsupported module operation in container: %s\n' "$*" >&2; return 2 ;;
    esac
}
export -f module
