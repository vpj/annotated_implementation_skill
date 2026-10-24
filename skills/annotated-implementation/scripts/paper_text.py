#!/usr/bin/env python3
"""
Save a paper's PDF and its extracted text into the project, so every phase can read and quote it.

Usage:
    paper_text.py 1412.6980 --out paper/                # arXiv id
    paper_text.py https://arxiv.org/abs/1412.6980 --out paper/
    paper_text.py path/to/paper.pdf --out paper/

Writes <out>/paper.pdf and <out>/paper.txt, with a `===== page N =====` line before each page.
Needs `pypdf` (pip install pypdf).
"""

import argparse
import re
import shutil
import sys
import urllib.request
from pathlib import Path

ARXIV_ID_RE = re.compile(r'(\d{4}\.\d{4,5})(v\d+)?')
USER_AGENT = 'annotated-implementation/1.0'


def arxiv_pdf_url(source: str):
    if source.startswith(('http://', 'https://')) and 'arxiv.org' not in source:
        return source
    m = ARXIV_ID_RE.search(source)
    if m:
        return f'https://arxiv.org/pdf/{m.group(1)}{m.group(2) or ""}'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', help='arXiv id, arXiv URL, PDF URL, or local PDF path')
    parser.add_argument('--out', type=Path, default=Path('paper'), help='output directory (default: paper/)')
    args = parser.parse_args()

    try:
        import pypdf
    except ImportError:
        print('error: pypdf is not installed; run `pip install pypdf`', file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    pdf_path = args.out / 'paper.pdf'

    local = Path(args.source)
    if local.is_file():
        shutil.copy(local, pdf_path)
    else:
        url = arxiv_pdf_url(args.source)
        if url is None:
            print(f'error: {args.source!r} is not a file, URL or arXiv id', file=sys.stderr)
            return 1
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(request) as response, open(pdf_path, 'wb') as f:
            shutil.copyfileobj(response, f)
        print(f'downloaded {url}')

    reader = pypdf.PdfReader(str(pdf_path))
    pages = [f'===== page {i} =====\n{page.extract_text() or ""}' for i, page in enumerate(reader.pages, 1)]
    text_path = args.out / 'paper.txt'
    text_path.write_text('\n\n'.join(pages), encoding='utf-8')
    print(f'wrote {pdf_path} and {text_path} ({len(reader.pages)} pages)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
