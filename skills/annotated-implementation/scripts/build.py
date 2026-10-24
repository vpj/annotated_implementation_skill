#!/usr/bin/env python3
"""
Build annotated implementation pages.

Each page is a `<name>.doc.html` annotation file. Its front matter may name a
plain Python file (`code: ../pkg/module.py`); the annotation's `<section>`
elements say which line of that file each section starts at. The script slices
the code at those lines, checks every slice against `data-expect`, and writes
a side-by-side HTML page.

Usage:
    build.py --listing pkg/module.py              # numbered listing to annotate
    build.py annotations/*.doc.html --out site    # validate and render
    build.py annotations/*.doc.html --check       # validate only

Standard library only.
"""

import argparse
import ast
import html
import io
import re
import shutil
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from highlight import highlight_python  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_DIR / 'assets'
TEMPLATE_PATH = ASSETS_DIR / 'template.html'
ASSET_FILES = ['style.css', 'annotate.js']
ASSET_OUT_DIR = 'assets'
DOC_SUFFIX = '.doc.html'

SECTION_RE = re.compile(r'<section\b((?:[^>"\']|"[^"]*"|\'[^\']*\')*)>(.*?)</section\s*>', re.S | re.I)
ATTR_RE = re.compile(r'([\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
COMMENT_RE = re.compile(r'<!--.*?-->', re.S)
HREF_RE = re.compile(r'\bhref\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)
ID_RE = re.compile(r'\bid\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)
ABSOLUTE_URL_RE = re.compile(r'^([a-z][a-z0-9+.-]*:|//)', re.I)
PLACEHOLDER_RE = re.compile(r'\{\{(\w+)\}\}')
SECTION_KINDS = ('doc', 'note')


class BuildError(Exception):
    pass


def line_of(text: str, offset: int, base: int) -> int:
    return base + text.count('\n', 0, offset)


def parse_front_matter(text: str, path: Path):
    """Parse `key: value` lines between two `---` lines at the top of the file."""
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        raise BuildError(f'{path}:1: file must start with front matter (a line containing ---)')
    meta = {}
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == '---':
            return meta, '\n'.join(lines[i + 1:]), i + 2
        if not line.strip():
            continue
        key, sep, value = line.partition(':')
        if not sep:
            raise BuildError(f'{path}:{i + 1}: expected "key: value" in front matter')
        meta[key.strip()] = value.strip()
    raise BuildError(f'{path}: front matter is not closed with ---')


def parse_sections(body: str, path: Path, base_line: int):
    """Split the annotation body into `<section>` elements; nothing else may appear outside them."""
    sections = []
    pos = 0
    for m in SECTION_RE.finditer(body):
        line = line_of(body, m.start(), base_line)
        outside = COMMENT_RE.sub('', body[pos:m.start()])
        if outside.strip():
            raise BuildError(f'{path}:{line_of(body, pos, base_line)}: content outside <section>: '
                             f'{outside.strip()[:60]!r}')
        if re.search(r'<section\b', m.group(2), re.I):
            raise BuildError(f'{path}:{line}: nested <section> elements are not allowed')
        attrs = {a.group(1): html.unescape(a.group(2) if a.group(2) is not None else a.group(3))
                 for a in ATTR_RE.finditer(m.group(1))}
        sections.append({'attrs': attrs,
                         'html': m.group(2).strip(),
                         'line': line})
        pos = m.end()
    outside = COMMENT_RE.sub('', body[pos:])
    if outside.strip():
        raise BuildError(f'{path}:{line_of(body, pos, base_line)}: content outside <section>: '
                         f'{outside.strip()[:60]!r}')
    if not sections:
        raise BuildError(f'{path}: no <section> elements found')
    return sections


def normalize(s: str) -> str:
    return ' '.join(s.split())


def expect_matches(line: str, expect: str) -> bool:
    """`data-expect` must appear in the start line, ignoring differences in whitespace."""
    return normalize(expect) in normalize(line)


def code_warnings(code: str, path: Path):
    """The code file should be plain: explanations belong in the annotation."""
    warnings = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.COMMENT and not tok.string.startswith('#!'):
                warnings.append(f'{path}:{tok.start[0]}: comment in code (move it to the annotation)')
    except (tokenize.TokenError, IndentationError):
        pass
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node, clean=False) is not None:
                warnings.append(f'{path}:{node.body[0].lineno}: docstring in code (move it to the annotation)')
    return warnings


def slice_code(sections, code_lines, doc_path: Path, code_path: Path):
    """Attach to each section the code from its start line up to the next section's start line."""
    n = len(code_lines)
    starts = []
    for s in sections:
        attrs = s['attrs']
        where = f'{doc_path}:{s["line"]}'
        if 'data-start' not in attrs:
            if 'data-expect' in attrs:
                raise BuildError(f'{where}: data-expect without data-start')
            continue
        try:
            start = int(attrs['data-start'])
        except ValueError:
            raise BuildError(f'{where}: data-start must be a line number, got {attrs["data-start"]!r}')
        if not 1 <= start <= n:
            raise BuildError(f'{where}: data-start={start} is outside {code_path} (1-{n})')
        if starts and start <= starts[-1][0]:
            raise BuildError(f'{where}: data-start={start} must be greater than the previous '
                             f'data-start={starts[-1][0]}')
        line = code_lines[start - 1]
        if not line.strip():
            raise BuildError(f'{where}: data-start={start} points at a blank line')
        if 'data-expect' not in attrs:
            raise BuildError(f'{where}: data-expect is required with data-start '
                             f'(line {start} is {line.strip()!r})')
        if not expect_matches(line, attrs['data-expect']):
            raise BuildError(f'{where}: data-expect={attrs["data-expect"]!r} does not match '
                             f'{code_path}:{start} which is {line.strip()!r}')
        starts.append((start, s))

    if not starts:
        raise BuildError(f'{doc_path}: names code {code_path} but no section has data-start')
    first = starts[0][0]
    uncovered = [i + 1 for i in range(first - 1) if code_lines[i].strip()]
    if uncovered:
        raise BuildError(f'{doc_path}: lines {uncovered[0]}-{first - 1} of {code_path} come before the '
                         f'first data-start and would not be shown; start a section at line {uncovered[0]}')

    for i, (start, s) in enumerate(starts):
        end = starts[i + 1][0] - 1 if i + 1 < len(starts) else n
        chunk = code_lines[start - 1:end]
        while chunk and not chunk[-1].strip():
            chunk.pop()
        s['code'] = (start, chunk)


def render_code(start: int, highlighted_lines) -> str:
    """Highlighted lines with inline line numbers, so numbers stay aligned when long lines wrap."""
    lines = [f'<span class="lineno">{start + i}</span>{line}' for i, line in enumerate(highlighted_lines)]
    return '<div class="highlight"><pre>' + '\n'.join(lines) + '</pre></div>'


def render_breadcrumbs(value: str) -> str:
    """`Overview=index.html; PPO=ppo.html` -> links."""
    links = []
    for item in value.split(';'):
        if not item.strip():
            continue
        label, _, url = item.partition('=')
        links.append(f'<a class="parent" href="{html.escape(url.strip())}">{html.escape(label.strip())}</a>')
    return '\n'.join(links)


def render_page(meta, sections, template: str) -> str:
    rows = []
    if meta.get('breadcrumbs'):
        rows.append(f'<div class="section header"><div class="docs"><nav class="breadcrumbs">'
                    f'{render_breadcrumbs(meta["breadcrumbs"])}</nav></div>'
                    f'<div class="code"></div></div>')
    for i, s in enumerate(sections):
        code = render_code(*s['code']) if s.get('code') else ''
        code_class = 'code' if code else 'code empty'
        is_doc = not meta.get('code') or s['attrs'].get('data-kind') == 'doc'
        docs_class = 'docs doc-strings' if is_doc else 'docs'
        rows.append(f'<div class="section" id="s{i}">\n'
                    f'<div class="{docs_class}"><a class="anchor" href="#s{i}">#</a>\n{s["html"]}\n</div>\n'
                    f'<div class="{code_class}">{code}</div>\n'
                    f'</div>')
    values = {'title': html.escape(meta['title']),
              'summary': html.escape(meta.get('summary', '')),
              'assets': ASSET_OUT_DIR,
              'page_class': '' if meta.get('code') else ' prose-only',
              'sections': '\n'.join(rows)}
    return PLACEHOLDER_RE.sub(lambda m: values[m.group(1)], template)


def build_page(doc_path: Path, template: str):
    if not doc_path.name.endswith(DOC_SUFFIX):
        raise BuildError(f'{doc_path}: annotation files must end with {DOC_SUFFIX}')
    meta, body, base_line = parse_front_matter(doc_path.read_text(encoding='utf-8'), doc_path)
    if not meta.get('title'):
        raise BuildError(f'{doc_path}: front matter needs a title')
    sections = parse_sections(body, doc_path, base_line)
    for s in sections:
        kind = s['attrs'].get('data-kind')
        if kind is not None and kind not in SECTION_KINDS:
            raise BuildError(f'{doc_path}:{s["line"]}: data-kind must be one of {", ".join(SECTION_KINDS)}, '
                             f'got {kind!r}')

    warnings = []
    if meta.get('code'):
        code_path = (doc_path.parent / meta['code']).resolve()
        if not code_path.is_file():
            raise BuildError(f'{doc_path}: code file {meta["code"]} not found (resolved to {code_path})')
        code = code_path.read_text(encoding='utf-8')
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise BuildError(f'{code_path}:{e.lineno}: syntax error: {e.msg}')
        warnings = code_warnings(code, code_path)
        slice_code(sections, code.split('\n'), doc_path, code_path)
        highlighted = highlight_python(code)
        for s in sections:
            if s.get('code'):
                start, chunk = s['code']
                s['code'] = (start, highlighted[start - 1:start - 1 + len(chunk)])
    else:
        for s in sections:
            if 'data-start' in s['attrs']:
                raise BuildError(f'{doc_path}:{s["line"]}: data-start used but front matter has no code:')

    ids, links = collect_links(meta, sections, doc_path)
    return {'name': doc_path.name[:-len(DOC_SUFFIX)],
            'html': render_page(meta, sections, template),
            'warnings': warnings,
            'ids': ids,
            'links': links}


def collect_links(meta, sections, doc_path: Path):
    """Element ids a link can target on this page, and every href in its prose and breadcrumbs."""
    ids = {f's{i}' for i in range(len(sections))}
    links = []
    for s in sections:
        ids.update(attr_value(m) for m in ID_RE.finditer(s['html']))
        links.extend((f'{doc_path}:{s["line"]}', attr_value(m)) for m in HREF_RE.finditer(s['html']))
    for item in meta.get('breadcrumbs', '').split(';'):
        url = item.partition('=')[2].strip()
        if url:
            links.append((f'{doc_path}: breadcrumbs', url))
    return ids, links


def attr_value(m) -> str:
    return html.unescape(m.group(1) if m.group(1) is not None else m.group(2))


def check_links(pages, out_dir):
    """
    Relative links must reach a page in this build (and an id on it) or a file in the output directory.
    A link to a page that is not in this build is only a warning, so a subset of pages can be built
    while the rest are still being written; a missing anchor on a page that is built is an error.
    """
    errors, warnings = [], []
    ids_by_page = {f'{p["name"]}.html': p['ids'] for p in pages}
    for page in pages:
        for where, href in page['links']:
            if not href or ABSOLUTE_URL_RE.match(href):
                continue
            target, _, anchor = href.partition('#')
            target = target.split('?')[0] or f'{page["name"]}.html'
            if target in ids_by_page:
                if anchor and anchor not in ids_by_page[target]:
                    errors.append(f'{where}: link {href!r}: {target} has no element with id {anchor!r}')
            elif out_dir is None or not (out_dir / target).exists():
                warnings.append(f'{where}: link {href!r} does not point to a page in this build'
                                + (f' or a file in {out_dir}' if out_dir is not None else ''))
    return errors, warnings


def listing(code_path: Path):
    lines = code_path.read_text(encoding='utf-8').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    width = len(str(len(lines)))
    for i, line in enumerate(lines, 1):
        print(f'{i:>{width}} | {line}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('files', nargs='+', type=Path, help='annotation files, or a Python file with --listing')
    parser.add_argument('--out', type=Path, help='output directory for the HTML pages')
    parser.add_argument('--check', action='store_true', help='validate without writing anything')
    parser.add_argument('--listing', action='store_true', help='print Python files with line numbers')
    args = parser.parse_args()

    if args.listing:
        for path in args.files:
            if len(args.files) > 1:
                print(f'==> {path} <==')
            listing(path)
        return 0

    if not args.check and args.out is None:
        parser.error('--out is required unless --check or --listing is given')

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    pages, errors = [], []
    for doc_path in args.files:
        try:
            page = build_page(doc_path, template)
            pages.append(page)
            for w in page['warnings']:
                print(f'warning: {w}', file=sys.stderr)
        except BuildError as e:
            errors.append(str(e))
    if not errors:
        link_errors, link_warnings = check_links(pages, args.out)
        errors.extend(link_errors)
        for w in link_warnings:
            print(f'warning: {w}', file=sys.stderr)

    for e in errors:
        print(f'error: {e}', file=sys.stderr)
    if errors:
        return 1

    if not args.check:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / ASSET_OUT_DIR).mkdir(exist_ok=True)
        for asset in ASSET_FILES:
            shutil.copy(ASSETS_DIR / asset, args.out / ASSET_OUT_DIR / asset)
        for page in pages:
            path = args.out / f'{page["name"]}.html'
            path.write_text(page['html'], encoding='utf-8')
            print(f'wrote {path}')
    else:
        print(f'ok: {len(pages)} page(s) valid')
    return 0


if __name__ == '__main__':
    sys.exit(main())
