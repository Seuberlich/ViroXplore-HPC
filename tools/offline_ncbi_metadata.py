#!/usr/bin/env python3
"""Build and query offline RefSeq GenBank accession/TaxID metadata.

Uses Python 3.6+ standard library; no NCBI EDirect or network calls at runtime.
GBFF metadata MUST match the exact FASTA used to build the Bowtie2 index.
"""
import argparse
import datetime
import gzip
import hashlib
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

VIRUS_TAXID = 10239
VERSION = '1'


def die(message):
    raise ValueError(message)


def load_nodes(path):
    parents = {}
    with open(str(path), encoding='utf-8') as inp:
        for line in inp:
            cols = [s.strip() for s in line.split('|')]
            if len(cols) < 2:
                continue
            try:
                parents[int(cols[0])] = int(cols[1])
            except ValueError:
                continue
    if VIRUS_TAXID not in parents or 1 not in parents:
        die('Taxonomy nodes.dmp lacks root 1 or Viruses 10239')
    return parents


def is_taxonomic_ancestor(ancestor, descendant, parents):
    """Test ancestry using the SAME local NCBI taxonomy snapshot as the DB."""
    visited = set()
    current = descendant
    while current not in visited:
        if current == ancestor:
            return True
        visited.add(current)
        parent = parents.get(current)
        if parent is None or parent == current:
            return False
        current = parent
    return False


def select_record_taxid(version, primary_organism, source_features, parents=None):
    """Resolve primary organism taxid without choosing among unrelated sources.

    GenBank records occasionally contain several `source` features (e.g. a
    composite sequence). Their TaxIDs are not interchangeable. When multiple
    matching /organism features have different TaxIDs, accept the uniquely
    most-specific DESCENDANT only if ALL candidates lie on its NCBI taxonomy
    lineage. Reject unrelated/conflicting TaxIDs, rather than guessing.
    """
    all_taxids = set()
    for source in source_features:
        all_taxids.update(source['taxids'])
    if len(all_taxids) == 1:
        return next(iter(all_taxids))
    if not all_taxids:
        die('GBFF record {} has no source TaxID'.format(version))
    primary = ' '.join((primary_organism or '').split()).casefold()
    candidates = set()
    if primary:
        for source in source_features:
            organism = ' '.join((source['organism'] or '').split()).casefold()
            if organism == primary:
                candidates.update(source['taxids'])
    if len(candidates) == 1:
        return next(iter(candidates))
    if len(candidates) > 1 and parents:
        # Example: a source annotated at both species and isolate levels.
        # Do not apply this rule to a different /organism or divergent taxa.
        most_specific = [
            child for child in candidates
            if all(is_taxonomic_ancestor(other, child, parents)
                   for other in candidates)
        ]
        if len(most_specific) == 1:
            chosen = most_specific[0]
            print('INFO: GBFF {} matching primary-organism TaxIDs {} form '
                  'one lineage; selected most-specific TaxID {}'
                  .format(version, sorted(candidates), chosen),
                  file=sys.stderr, flush=True)
            return chosen
    die('GBFF record {} has {} source TaxIDs; primary organism {!r} '
        'cannot be resolved unambiguously (matching TaxIDs: {}). '
        'Inspect this GenBank record instead of selecting an arbitrary TaxID.'
        .format(version, len(all_taxids), primary_organism,
                sorted(candidates)))


def read_gbff_records(path, parents=None):
    """Yield (versioned accession, PRIMARY taxid, definition), no sequence."""
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(str(path), 'rt', encoding='utf-8', errors='replace') as inp:
        version = None
        definition = []
        in_definition = False
        primary_organism = None
        source_features = []
        current_source = None
        organism_continuation = False
        for line in inp:
            if line.startswith('LOCUS       '):
                version = None
                definition = []
                in_definition = False
                primary_organism = None
                source_features = []
                current_source = None
                organism_continuation = False
            elif line.startswith('DEFINITION  '):
                definition = [line[12:].strip()]
                in_definition = True
            elif in_definition and line.startswith('            '):
                definition.append(line.strip())
            elif in_definition:
                in_definition = False
            if line.startswith('  ORGANISM  '):
                primary_organism = line[12:].strip()
            if line.startswith('VERSION     '):
                fields = line.split()
                if len(fields) >= 2:
                    version = fields[1]
            # FEATURE keys start in column 6 and qualifiers are indented.
            # Collect TaxIDs separately for each source feature rather than
            # mixing TaxIDs from all features into one record-wide set.
            if re.match(r'^     [A-Za-z_]+\s', line):
                current_source = None
                organism_continuation = False
                if re.match(r'^     source\s', line):
                    current_source = {'organism': None, 'taxids': set()}
                    source_features.append(current_source)
            if line.startswith('ORIGIN'):
                current_source = None
                organism_continuation = False
            if current_source is not None:
                for match in re.finditer(r'/db_xref="taxon:(\d+)"', line):
                    current_source['taxids'].add(int(match.group(1)))
                m = re.search(r'/organism="(.*)', line)
                if m:
                    part = m.group(1)
                    if '"' in part:
                        current_source['organism'] = part.split('"', 1)[0]
                        organism_continuation = False
                    else:
                        current_source['organism'] = part.strip()
                        organism_continuation = True
                elif organism_continuation:
                    part = line.strip()
                    if '"' in part:
                        current_source['organism'] += ' ' + part.split('"', 1)[0]
                        organism_continuation = False
                    else:
                        current_source['organism'] += ' ' + part
            if line.startswith('//'):
                if version is None or not re.match(r'^[A-Za-z][A-Za-z0-9_]*\.\d+$', version):
                    die('GBFF record without valid VERSION in {}'.format(path))
                taxid = select_record_taxid(version, primary_organism, source_features, parents)
                title = ' '.join(' '.join(definition).split()).rstrip()
                if not title:
                    die('GBFF record {} has no DEFINITION'.format(version))
                yield version, taxid, title
                version = None
                definition = []
                source_features = []
                current_source = None


def load_scientific_names(path, wanted):
    names = {}
    with open(str(path), encoding='utf-8') as inp:
        for line in inp:
            cols = [s.strip() for s in line.split('|')]
            if len(cols) >= 4 and cols[3] == 'scientific name':
                try:
                    taxid = int(cols[0])
                except ValueError:
                    continue
                if taxid in wanted:
                    names[taxid] = cols[1]
    return names


def virus_ancestry(taxid, parents, cache):
    chain = []
    current = taxid
    result = False
    while True:
        if current in cache:
            result = cache[current]
            break
        if current == VIRUS_TAXID:
            result = True
            break
        if current == 1:
            break
        if current not in parents:
            die('TaxID {} not found in nodes.dmp'.format(current))
        if current in chain:
            die('Taxonomy cycle encountered for {}'.format(taxid))
        chain.append(current)
        current = parents[current]
    for item in chain:
        cache[item] = result
    cache[taxid] = result
    return result


def sha256(path):
    digest = hashlib.sha256()
    with open(str(path), 'rb') as inp:
        for chunk in iter(lambda: inp.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def build(args):
    ref = Path(args.reference_fasta)
    nodes = Path(args.nodes)
    names = Path(args.names)
    gbffs = [Path(x) for x in args.gbff]
    for p in [ref, nodes, names] + gbffs:
        if not p.is_file() or p.stat().st_size == 0:
            die('Missing/empty input file: {}'.format(p))
    dest = Path(args.database)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmpname = tempfile.mkstemp(prefix=dest.name + '.building.', suffix='.sqlite', dir=str(dest.parent))
    os.close(fd)
    try:
        con = sqlite3.connect(tmpname)
        try:
            con.execute('PRAGMA journal_mode=DELETE')
            con.execute('CREATE TABLE accessions (accession TEXT PRIMARY KEY, taxid INTEGER NOT NULL, title TEXT NOT NULL)')
            con.execute('CREATE TABLE taxonomy (taxid INTEGER PRIMARY KEY, scientific_name TEXT NOT NULL, division TEXT NOT NULL)')
            con.execute('CREATE TABLE info (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            con.execute('CREATE TABLE fasta_accessions (accession TEXT PRIMARY KEY)')
            parents = load_nodes(nodes)
            count = 0
            for path in gbffs:
                print('Reading GBFF:', path, flush=True)
                for accession, taxid, title in read_gbff_records(path, parents):
                    prev = con.execute('SELECT taxid, title FROM accessions WHERE accession=?', (accession,)).fetchone()
                    if prev:
                        if prev != (taxid, title):
                            die('Conflicting GBFF records for {}'.format(accession))
                    else:
                        con.execute('INSERT INTO accessions VALUES (?, ?, ?)', (accession, taxid, title))
                        count += 1
                con.commit()
            if not count:
                die('No GBFF records found')
            print('GBFF accession records:', count, flush=True)
            fasta_total = 0
            with open(str(ref), encoding='ascii') as fasta:
                for line in fasta:
                    if not line.startswith('>'):
                        continue
                    accession = line[1:].split(None, 1)[0]
                    if not accession:
                        die('Empty FASTA record identifier')
                    try:
                        con.execute('INSERT INTO fasta_accessions VALUES (?)', (accession,))
                    except sqlite3.IntegrityError:
                        die('Duplicate FASTA identifier: {}'.format(accession))
                    fasta_total += 1
            if not fasta_total:
                die('RefSeq FASTA is empty')
            missing_count = con.execute('''SELECT COUNT(*) FROM fasta_accessions AS f
                            LEFT JOIN accessions AS a ON a.accession=f.accession
                            WHERE a.accession IS NULL''').fetchone()[0]
            if missing_count:
                examples = con.execute('''SELECT f.accession FROM fasta_accessions AS f
                            LEFT JOIN accessions AS a ON a.accession=f.accession
                            WHERE a.accession IS NULL LIMIT 8''').fetchall()
                die('RefSeq FASTA/GBFF snapshot mismatch: {} / {} FASTA accessions missing from GBFF; examples: {}. Download metadata from SAME RefSeq release as indexed FASTA, or rebuild the reference and index together.'.format(missing_count, fasta_total, [r[0] for r in examples]))
            wanted = set(r[0] for r in con.execute('SELECT DISTINCT taxid FROM accessions'))
            scientific_names = load_scientific_names(names, wanted)
            missing_names = wanted - set(scientific_names)
            if missing_names:
                die('Taxonomy names.dmp missing {} GBFF TaxIDs; examples {}'.format(len(missing_names), sorted(missing_names)[:8]))
            cache = {VIRUS_TAXID: True, 1: False}
            for taxid in sorted(wanted):
                division = 'Viruses' if virus_ancestry(taxid, parents, cache) else 'Other'
                con.execute('INSERT INTO taxonomy VALUES (?, ?, ?)', (taxid, scientific_names[taxid], division))
            for key, value in [
                ('format_version', VERSION),
                ('created_utc', datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')),
                ('reference_fasta_sha256', sha256(ref)),
                ('taxonomy_nodes_sha256', sha256(nodes)),
                ('taxonomy_names_sha256', sha256(names)),
                ('fasta_records', str(fasta_total)),
                ('gbff_records', str(count)),
                ('gbff_files', ','.join(str(x.name) for x in gbffs)),
            ]:
                con.execute('INSERT INTO info VALUES (?, ?)', (key, value))
            for index, path in enumerate(gbffs):
                con.execute('INSERT INTO info VALUES (?, ?)', ('gbff_sha256_{}'.format(index), sha256(path)))
            con.execute('DROP TABLE fasta_accessions')
            con.commit()
            check = con.execute('PRAGMA integrity_check').fetchone()[0]
            if check != 'ok':
                die('SQLite integrity_check failed: {}'.format(check))
            print('PASS: {} / {} FASTA references have offline metadata; {} TaxIDs'.format(fasta_total, fasta_total, len(wanted)), flush=True)
            print('RefSeq FASTA SHA256:', con.execute("SELECT value FROM info WHERE key='reference_fasta_sha256'").fetchone()[0], flush=True)
        finally:
            con.close()
        os.replace(tmpname, str(dest))
        print('Offline metadata DB:', dest, flush=True)
    except Exception:
        if os.path.exists(tmpname):
            os.unlink(tmpname)
        raise


def lookup(args):
    db = Path(args.database)
    if not db.is_file() or db.stat().st_size == 0:
        die('Offline metadata missing: {}. Run setup_refseq_offline_metadata.sh before pipeline.'.format(db))
    con = sqlite3.connect('file:{}?mode=ro'.format(db.absolute()), uri=True)
    try:
        info = dict(con.execute('SELECT key, value FROM info'))
        if info.get('format_version') != VERSION:
            die('Unsupported offline metadata schema version')
        if args.reference_fasta:
            ref_hash = sha256(Path(args.reference_fasta))
            if ref_hash != info.get('reference_fasta_sha256'):
                die('Offline metadata DB was built for a DIFFERENT reference FASTA. Rebuild matching metadata before analysis.')
        requested = []
        seen = set()
        with open(args.accessions, encoding='ascii') as inp:
            for line in inp:
                acc = line.strip()
                if not acc:
                    continue
                if acc in seen:
                    continue
                seen.add(acc)
                requested.append(acc)
        accessions = []
        taxonomy = {}
        missing = []
        for acc in requested:
            record = con.execute('''SELECT a.taxid, a.title, t.scientific_name, t.division
                                    FROM accessions a JOIN taxonomy t ON t.taxid = a.taxid
                                    WHERE a.accession=?''', (acc,)).fetchone()
            if record is None:
                missing.append(acc)
                continue
            taxid, title, scientific_name, division = record
            accessions.append('{}\t{}\t{}'.format(acc, taxid, title))
            taxonomy[taxid] = '{}\t{}\t{}'.format(taxid, scientific_name, division)
        if missing:
            die('{} / {} mapped accessions have no local metadata (examples: {}). RefSeq metadata and Bowtie2 index must originate from the same release.'.format(len(missing), len(requested), ', '.join(missing[:10])))
        with open(args.accession_output, 'w', encoding='utf-8') as out:
            for line in accessions:
                out.write(line + '\n')
        with open(args.taxonomy_output, 'w', encoding='utf-8') as out:
            for taxid in sorted(taxonomy):
                out.write(taxonomy[taxid] + '\n')
        print('Offline accession metadata validated: {} unique identifiers'.format(len(accessions)), flush=True)
        print('Offline taxonomy metadata validated: {} unique identifiers'.format(len(taxonomy)), flush=True)
    finally:
        con.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command')
    buildp = sub.add_parser('build')
    buildp.add_argument('--reference-fasta', required=True)
    buildp.add_argument('--gbff', nargs='+', required=True)
    buildp.add_argument('--nodes', required=True)
    buildp.add_argument('--names', required=True)
    buildp.add_argument('--database', required=True)
    look = sub.add_parser('lookup')
    look.add_argument('--database', required=True)
    look.add_argument('--reference-fasta', help='optional SHA256 consistency check')
    look.add_argument('--accessions', required=True)
    look.add_argument('--accession-output', required=True)
    look.add_argument('--taxonomy-output', required=True)
    args = parser.parse_args(argv)
    if args.command not in ('build', 'lookup'):
        parser.print_help()
        return 2
    try:
        if args.command == 'build':
            build(args)
        else:
            lookup(args)
    except (ValueError, OSError, sqlite3.Error) as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
