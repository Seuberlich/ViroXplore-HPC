#!/usr/bin/env python3
"""Conservative classification of DIAMOND viral-nr hits, then best eligible hit.

Python 3.8+, standard library only. No external queries or network required.

This is NOT a definitive biological host-range classifier. Exclusions are based
on explicit bacterial/archaeal-virus naming or clearly prokaryotic viral taxa.
Ambiguous or missing assignments are sent to review, never silently discarded.
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

VIRUS_ROOT = 10239
BACTERIA_ROOT = 2
ARCHAEA_ROOT = 2157

# Taxonomic groups known to include viruses of bacteria/archaea. In particular
# Caudoviricetes includes both tailed bacterial viruses and archaeal viruses.
# Keep this list conservative: broader viral realms contain eukaryotic viruses.
PROK_GROUPS = {
    'caudoviricetes', 'caudovirales', 'myoviridae', 'siphoviridae', 'podoviridae',
    'leviviricetes', 'leviviridae', 'microviridae', 'inoviridae',
    'cystoviridae', 'tectiviridae', 'corticoviridae', 'plasmaviridae',
    'fuselloviridae', 'lipothrixviridae', 'rudiviridae', 'bicaudaviridae',
    'guttaviridae', 'ampullaviridae', 'globuloviridae', 'clavaviridae',
    'spiraviridae', 'tristromaviridae', 'pleolipoviridae', 'sphaerolipoviridae',
    'portogloboviridae', 'thalassaviridae', 'halspiviridae',
}
# Indications in TAXON scientific names (or their parent taxa), NOT protein titles.
PHAGE_RE = re.compile(r'\b(?:bacteriophage|phage|phages)\b', re.I)
ARCHAEAL_RE = re.compile(
    r'\b(?:archaeal|archaeon|archaeovirus|halovirus|haloarchaeal)\b|'
    r'\b(?:sulfolobus|saccharolobus|acidianus|aeropyrum|pyrobaculum|'
    r'thermoproteus|methanococcus|methanobacterium|methanocaldococcus|'
    r'halobacterium|haloarcula|halorubrum|haloferax|halogeometricum|'
    r'halorhabdus|haloterrigena)\b.*\bvirus\b',
    re.I)
NODE_META = re.compile(r'_length_(\d+)_cov_([^\s_]+)')


def read_taxdump(folder):
    folder = Path(folder)
    parents = {}
    names = {}
    merged = {}
    for line in (folder / 'nodes.dmp').open(encoding='utf-8'):
        fields = [x.strip() for x in line.split('|')]
        if len(fields) >= 2:
            parents[int(fields[0])] = int(fields[1])
    for line in (folder / 'names.dmp').open(encoding='utf-8'):
        fields = [x.strip() for x in line.split('|')]
        if len(fields) >= 4 and fields[3] == 'scientific name':
            names[int(fields[0])] = fields[1]
    merged_file = folder / 'merged.dmp'
    if merged_file.exists():
        for line in merged_file.open(encoding='utf-8'):
            fields = [x.strip() for x in line.split('|')]
            if len(fields) >= 2:
                merged[int(fields[0])] = int(fields[1])
    if VIRUS_ROOT not in parents:
        raise RuntimeError('Taxonomy nodes.dmp lacks viruses TaxID 10239')
    return parents, names, merged


class TaxonomyClassifier:
    def __init__(self, folder):
        self.parents, self.names, self.merged = read_taxdump(folder)
        self.cache = {}

    def one(self, taxid):
        if taxid in self.cache:
            return self.cache[taxid]
        original = taxid
        taxid = self.merged.get(taxid, taxid)
        if taxid not in self.parents:
            result = ('review', 'taxid_not_in_nodes', self.names.get(taxid, ''))
            self.cache[original] = result
            return result
        current = taxid
        lineage = []
        visited = set()
        while current not in visited:
            visited.add(current)
            lineage.append(current)
            parent = self.parents.get(current)
            if parent is None or parent == current:
                break
            current = parent
        taxname = self.names.get(taxid, '')
        if VIRUS_ROOT not in lineage:
            reason = 'nonviral_taxonomy' if BACTERIA_ROOT in lineage or ARCHAEA_ROOT in lineage else 'outside_virus_root'
            result = ('exclude' if reason == 'nonviral_taxonomy' else 'review', reason, taxname)
        else:
            names = [self.names.get(t, '') for t in lineage]
            decisive = next((n for n in names if n.casefold() in PROK_GROUPS), None)
            if decisive:
                result = ('exclude', 'prokaryotic_viral_lineage:' + decisive, taxname)
            else:
                decisive = next((n for n in names if PHAGE_RE.search(n)), None)
                if decisive:
                    result = ('exclude', 'phage_taxon_name:' + decisive, taxname)
                else:
                    decisive = next((n for n in names if ARCHAEAL_RE.search(n)), None)
                    if decisive:
                        result = ('exclude', 'archaeal_virus_taxon_name:' + decisive, taxname)
                    elif taxid == VIRUS_ROOT:
                        result = ('review', 'unspecified_viral_taxonomy', taxname)
                    else:
                        result = ('keep', 'viral_taxonomy_not_known_prokaryotic', taxname)
        self.cache[original] = result
        return result

    def multi(self, raw):
        if not raw or raw in ('0', 'N/A', '-'):
            return 'review', 'missing_staxids', ''
        tid_list = []
        for part in raw.split(';'):
            try:
                tid_list.append(int(part))
            except ValueError:
                return 'review', 'invalid_staxids', ''
        if not tid_list:
            return 'review', 'missing_staxids', ''
        assessments = [self.one(x) for x in tid_list]
        decisions = {x[0] for x in assessments}
        label = ';'.join(dict.fromkeys(x[2] for x in assessments if x[2]))
        if decisions == {'keep'}:
            return 'keep', 'all_taxids_viral_nonprokaryotic', label
        if decisions == {'exclude'}:
            return 'exclude', ';'.join(dict.fromkeys(x[1] for x in assessments)), label
        return 'review', 'mixed_or_uncertain_taxids:' + ','.join(sorted(decisions)), label


def fasta_records(path):
    with open(path, encoding='utf-8') as fh:
        name, header, sequence = None, None, []
        for line in fh:
            if line.startswith('>'):
                if name is not None:
                    yield name, header, ''.join(sequence)
                header = line[1:].rstrip('\n\r')
                name = header.split()[0]
                sequence = []
            else:
                sequence.append(line.strip())
        if name is not None:
            yield name, header, ''.join(sequence)


def numeric_float(x, fallback=0.0):
    try:
        return float(x)
    except (ValueError, TypeError):
        return fallback


def row_sort_key(row):
    # Best bitscore, smallest E value, longest alignment, then stable accession.
    return (-numeric_float(row['bitscore']), numeric_float(row['evalue'], float('inf')),
            -numeric_float(row['alignment_length']), row['subject_accession'])


def run(args):
    clf = TaxonomyClassifier(args.taxonomy)
    sample = args.sample
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    prefix = output / sample
    columns = ['query_id', 'subject_accession', 'staxids', 'subject_title',
               'percent_identity', 'alignment_length', 'evalue', 'bitscore',
               'decision', 'reason', 'taxon_names']
    raw_columns = columns[:8]
    allhits_path = Path(str(prefix) + '_DMND_hits_classified.tsv')
    excluded_path = Path(str(prefix) + '_DMND_hits_excluded.tsv')
    review_path = Path(str(prefix) + '_DMND_hits_review.tsv')
    best_path = Path(str(prefix) + '_DMND_best_eukaryotic_viral_hits.tsv')
    final_path = Path(str(prefix) + '_DMNDtable_viruses_final.xls')
    reviewbest_path = Path(str(prefix) + '_DMNDtable_review.tsv')
    finalfasta_path = Path(args.final_fasta)
    summary_path = Path(str(prefix) + '_DMND_filter_summary.json')
    best_keep = {}
    best_review = {}
    counters = Counter()
    reasons = Counter()
    query_decisions = defaultdict(set)
    with (allhits_path.open('w', encoding='utf-8', newline='') as allf,
          excluded_path.open('w', encoding='utf-8', newline='') as exf,
          review_path.open('w', encoding='utf-8', newline='') as revf):
        allw = csv.DictWriter(allf, fieldnames=columns, delimiter='\t', extrasaction='ignore')
        exw = csv.DictWriter(exf, fieldnames=columns, delimiter='\t', extrasaction='ignore')
        revw = csv.DictWriter(revf, fieldnames=columns, delimiter='\t', extrasaction='ignore')
        for writer in (allw, exw, revw):
            writer.writeheader()
        with Path(args.hits).open(encoding='utf-8') as raw:
            for line_no, line in enumerate(raw, 1):
                if not line.strip():
                    continue
                values = line.rstrip('\n\r').split('\t')
                if len(values) != len(raw_columns):
                    raise RuntimeError(f'Invalid DIAMOND tabular row {line_no}: '
                                       f'expected 8 columns, found {len(values)}')
                row = dict(zip(raw_columns, values))
                decision, reason, label = clf.multi(row['staxids'])
                row.update(decision=decision, reason=reason, taxon_names=label)
                allw.writerow(row)
                counters[decision] += 1
                reasons[reason] += 1
                query_decisions[row['query_id']].add(decision)
                if decision == 'exclude':
                    exw.writerow(row)
                elif decision == 'review':
                    revw.writerow(row)
                    prev = best_review.get(row['query_id'])
                    if prev is None or row_sort_key(row) < row_sort_key(prev):
                        best_review[row['query_id']] = row
                else:
                    prev = best_keep.get(row['query_id'])
                    if prev is None or row_sort_key(row) < row_sort_key(prev):
                        best_keep[row['query_id']] = row
    if counters['keep'] + counters['exclude'] + counters['review'] and counters['review'] == sum(counters.values()):
        raise RuntimeError('All DIAMOND hits require manual review: '
                           'check that the .dmnd file contains usable taxonomy metadata (staxids)')
    with best_path.open('w', encoding='utf-8', newline='') as out:
        w = csv.DictWriter(out, fieldnames=columns, delimiter='\t', extrasaction='ignore')
        w.writeheader()
        for qid, row in sorted(best_keep.items()):
            w.writerow(row)
    with reviewbest_path.open('w', encoding='utf-8', newline='') as out:
        w = csv.DictWriter(out, fieldnames=columns, delimiter='\t', extrasaction='ignore')
        w.writeheader()
        for qid, row in sorted(best_review.items()):
            w.writerow(row)

    # Build sequence dictionary only from assembly, not from the DIAMOND subject sequences.
    retained = set(best_keep)
    sequences = {}
    sequence_count = 0
    for qid, header, seq in fasta_records(args.assembly):
        sequence_count += 1
        if qid in retained:
            sequences[qid] = (header, seq)
    not_found = retained - set(sequences)
    if not_found:
        raise RuntimeError(f'{len(not_found)} selected DIAMOND query IDs absent from assembly FASTA, '
                           f'for example: {next(iter(not_found))}')
    finalfasta_path.parent.mkdir(parents=True, exist_ok=True)
    # Write output tables after validation. The final table retains the *original* 7 columns.
    with finalfasta_path.open('w', encoding='utf-8') as out:
        for qid in sorted(sequences):
            hdr, seq = sequences[qid]
            out.write('>' + hdr + '\n')
            for i in range(0, len(seq), 80):
                out.write(seq[i:i+80] + '\n')
    final_columns = ['id', 'nodelength', 'nodekmercov', 'seq', 'blastx_besthit',
                     'blastx_identity', 'blastx_lengthalignment']
    with final_path.open('w', encoding='utf-8', newline='') as out:
        w = csv.writer(out, delimiter='\t')
        w.writerow(final_columns)
        for qid, row in sorted(best_keep.items()):
            _, seq = sequences[qid]
            match = NODE_META.search(qid)
            seq_len = match.group(1) if match else str(len(seq))
            cov = match.group(2) if match else 'NA'
            w.writerow([qid, seq_len, cov, seq, row['subject_title'].replace(' ', '_'),
                        row['percent_identity'], row['alignment_length']])
    report = {
        'sample': sample,
        'assembly_fasta_records': sequence_count,
        'diamond_hit_rows': sum(counters.values()),
        'hit_decisions': dict(counters),
        'decision_reasons': dict(reasons),
        'query_ids_with_hits': len(query_decisions),
        'retained_query_ids': len(best_keep),
        'review_query_ids': len(best_review),
        'excluded_hit_rows': counters['exclude'],
        'note': 'Uncertain/mixed TaxID assignments remain in the separate review table; '
                'best-hit selection is performed after filtering.'
    }
    summary_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print('Final result:', final_path)
    print('Selected assembly sequences:', finalfasta_path)
    if not best_keep:
        print('WARNING: no confident non-prokaryotic viral hits were retained.', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--hits', required=True, help='DIAMOND 8-field TSV output')
    ap.add_argument('--taxonomy', required=True, help='Directory containing nodes.dmp, names.dmp')
    ap.add_argument('--assembly', required=True, help='Assembly FASTA used as DIAMOND query')
    ap.add_argument('--sample', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--final-fasta', required=True)
    args = ap.parse_args()
    try:
        run(args)
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
