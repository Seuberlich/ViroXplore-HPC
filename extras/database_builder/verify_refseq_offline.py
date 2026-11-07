#!/usr/bin/env python3
"""Read-only, no-network ViroXplore-HPC RefSeq and SQLite metadata verifier (Python 3.6+)."""
import argparse
import hashlib
import os
import sqlite3
import sys
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with open(str(path), 'rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify(root):
    refdir = root / 'refseq_viral'
    fasta = refdir / 'refseq_viral.fna'
    db = refdir / 'refseq_viral_metadata.sqlite'
    required = [fasta, db, refdir / 'refseq_viral.fna.masked.bed',
                refdir / 'refseq_viral.fna.10homopolymers.bed',
                refdir / 'contam_suppl_table_3.taxids.list']
    for path in required:
        if not path.is_file() or (path in (fasta, db) and path.stat().st_size == 0):
            raise ValueError('Missing reference file: {}'.format(path))
    for extension in ('bt2', 'bt2l'):
        if all((refdir / ('refseq_viral.fna.{}.{}'.format(part, extension))).is_file() and
               (refdir / ('refseq_viral.fna.{}.{}'.format(part, extension))).stat().st_size > 0
               for part in ('1', '2', '3', '4', 'rev.1', 'rev.2')):
            print('PASS: six Bowtie2 index files ({})'.format(extension))
            break
    else:
        raise ValueError('Missing/incomplete Bowtie2 .bt2/.bt2l index')
    uri = db.resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as con:
        con.execute('PRAGMA query_only=ON')
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise ValueError('SQLite integrity check failed: {}'.format(integrity))
        info = dict(con.execute('SELECT key, value FROM info'))
        if info.get('format_version') != '1':
            raise ValueError('Unsupported SQLite schema version: {}'.format(info.get('format_version')))
        actual_hash = sha256(fasta)
        if actual_hash != info.get('reference_fasta_sha256'):
            raise ValueError('RefSeq FASTA does not match offline SQLite metadata SHA256')
        fasta_count = 0
        missing = []
        with open(str(fasta), encoding='ascii') as stream:
            for line in stream:
                if not line.startswith('>'):
                    continue
                accession = line[1:].split(None, 1)[0]
                fasta_count += 1
                if con.execute('SELECT 1 FROM accessions a JOIN taxonomy t ON t.taxid=a.taxid WHERE a.accession=?',
                               (accession,)).fetchone() is None:
                    missing.append(accession)
                    if len(missing) >= 8:
                        break
        if missing:
            raise ValueError('Missing offline metadata for FASTA accessions (first examples): {}'.format(', '.join(missing)))
        if fasta_count == 0 or str(fasta_count) != info.get('fasta_records'):
            raise ValueError('FASTA record count {} differs from SQLite manifest {}'.format(
                fasta_count, info.get('fasta_records')))
        taxids = con.execute('SELECT COUNT(*) FROM taxonomy').fetchone()[0]
        print('PASS: SQLite integrity, format version, and reference SHA256')
        print('PASS: {} / {} FASTA accessions annotated; {} taxonomy records'.format(
            fasta_count, fasta_count, taxids))
        print('RefSeq FASTA SHA256: {}'.format(actual_hash))
        print('PASS: offline check complete; no network requests made')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference_root', help='Absolute directory holding refseq_viral/')
    args = parser.parse_args()
    if not os.path.isabs(args.reference_root):
        parser.error('reference_root must be absolute')
    try:
        verify(Path(args.reference_root))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print('FAIL: {}'.format(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
