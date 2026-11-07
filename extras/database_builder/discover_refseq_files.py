#!/usr/bin/env python3
"""Discover NCBI RefSeq release/viral genomic FASTA archives from its HTTPS listing.

Compatible with Python >=3.6; do not blindly assume a single numbered file.
"""
from html.parser import HTMLParser
from urllib.request import urlopen
from urllib.parse import urljoin, urlsplit
import re
import sys

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href' and value:
                    self.links.append(value)


def discover(base, html):
    parser = Links()
    parser.feed(html)
    pattern = re.compile(r'^viral\.[0-9]+(?:\.[0-9]+)?\.genomic\.fna\.gz$')
    matched = set()
    for link in parser.links:
        url = urljoin(base, link)
        if urlsplit(url).netloc != urlsplit(base).netloc:
            continue
        filename = urlsplit(url).path.rsplit('/', 1)[-1]
        if pattern.fullmatch(filename):
            matched.add(url)
    return sorted(matched)


def main():
    if len(sys.argv) != 2:
        sys.exit('Usage: discover_refseq_files.py HTTPS_REFSEQ_RELEASE_URL')
    base = sys.argv[1].rstrip('/') + '/'
    if not base.startswith('https://'):
        sys.exit('ERROR: HTTPS URL required')
    with urlopen(base, timeout=90) as req:
        html = req.read().decode('utf-8', errors='replace')
    files = discover(base, html)
    if not files:
        sys.exit('ERROR: No genomic RefSeq viral FASTA files in the directory listing')
    for url in files:
        print(url)

if __name__ == '__main__':
    main()
