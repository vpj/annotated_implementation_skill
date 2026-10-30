#!/usr/bin/env python3
"""
Build the annotated HTML of a Python package.

Every Python file `pkg/x.py` is annotated by `pkg/x.doc.html`, next to it. The
annotation's `<section>` elements say which line of the Python file each section
starts at. The script slices the code at those lines, checks every slice against
`data-expect`, and writes a side-by-side `x.html`. The output mirrors the package:
`pkg/sub/x.py` becomes `<out>/sub/x.html`, and `__init__.py` becomes `index.html`.

Usage:
    build.py --listing pkg/module.py    # numbered listing to annotate
    build.py pkg --out site             # validate and render
    build.py pkg --check                # validate only

Standard library only.
"""

import argparse
import ast
import html
import io
import posixpath
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
FRONT_MATTER_KEYS = ('title', 'summary', 'breadcrumbs')

SECTION_RE = re.compile(r'<section\b((?:[^>"\']|"[^"]*"|\'[^\']*\')*)>(.*?)</section\s*>', re.S | re.I)
ATTR_RE = re.compile(r'([\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
COMMENT_RE = re.compile(r'<!--.*?-->', re.S)
HREF_RE = re.compile(r'\bhref\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)
ID_RE = re.compile(r'\bid\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I)
ABSOLUTE_URL_RE = re.compile(r'^([a-z][a-z0-9+.-]*:|//)', re.I)
PLACEHOLDER_RE = re.compile(r'\{\{(\w+)\}\}')
SECTION_KINDS = ('doc', 'note')
PAPER_LABEL_RE = re.compile(r'\b(?:Eqs?|Equations?|Figs?|Figures?|Tables?|Alg|Algorithms?|Sections?|Sec|Appendix'
                            r'|Theorems?|Lemmas?|Corollary|Corollaries|Propositions?|Definitions?)\.?'
                            r'\s*\(?[A-Z]?\d+(?:\.\d+)*\b')
PAPER_REF_SPAN_RE = re.compile(r'<span\b[^>]*\bclass\s*=\s*["\'][^"\']*\bpaper-ref\b[^>]*>.*?</span\s*>', re.S | re.I)
MATH_RE = re.compile(r'\$\$.*?\$\$|\$[^$]*\$|\\\[.*?\\\]|\\\(.*?\\\)|\\begin\{(\w+\*?)\}.*?\\end\{\1\}', re.S)
TAG_RE = re.compile(r'<[^>]+>')


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


SUBHEADING_RE = re.compile(r'<h[2-4][\s>]', re.I)


def definition_warnings(sections, code: str, doc_path: Path):
    """
    Each top-level function and class gets its own section, so a heading or note never has to explain
    code the reader cannot tell apart. A heading that covers several definitions goes in a section without
    data-start, or the definitions belong together in a class.
    """
    starts = []
    for node in ast.parse(code).body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            starts.append((first, node.name))
    warnings = []
    # A decorator is part of its definition: a section that starts between the first decorator and the
    # `def`/`class` line leaves the decorator alone beside the previous section's prose.
    decorated = [
        (min(d.lineno for d in node.decorator_list), node.lineno, node.name)
        for node in ast.walk(ast.parse(code))
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.decorator_list
    ]
    for s in sections:
        if s.get('code'):
            start = s['code'][0]
            for first, line, name in decorated:
                if first < start <= line:
                    warnings.append(f'{doc_path}:{s["line"]}: section starts at line {start}, inside the definition '
                                    f'of {name}, whose decorator is at line {first}; start one section at line '
                                    f'{first} for the decorator and the definition together')
    heading_on_code = None
    for s in sections:
        has_heading = SUBHEADING_RE.search(s['html']) is not None
        if not s.get('code'):
            if has_heading:
                heading_on_code = None
            continue
        start, chunk = s['code']
        names = [name for line, name in starts if start <= line < start + len(chunk)]
        if len(names) > 1:
            warnings.append(f'{doc_path}:{s["line"]}: section covers {len(names)} definitions '
                            f'({", ".join(names)}); start a section at each one, put a heading that covers '
                            f'several of them in a section without data-start, or group them in a class')
        opens_definition = any(line == start for line, _ in starts)
        if has_heading:
            heading_on_code = names[0] if opens_definition and names else None
        elif opens_definition and heading_on_code is not None:
            warnings.append(f'{doc_path}:{s["line"]}: {names[0]} has no heading and sits under the heading of '
                            f'{heading_on_code}; give it its own heading, or move the shared heading into a '
                            f'section without data-start above both')
    return warnings


def paper_reference_warnings(sections, path: Path):
    """
    The reader does not have the paper open, so a bare "Eq. 3" or "Algorithm 1" tells them nothing.
    Prose must state what it refers to (or link an anchor on this site); the paper's own label may
    appear only inside <span class="paper-ref">, next to the content it labels.
    """
    warnings = []
    for s in sections:
        text = PAPER_REF_SPAN_RE.sub(' ', COMMENT_RE.sub(' ', s['html']))
        text = html.unescape(TAG_RE.sub(' ', MATH_RE.sub(' ', text)))
        for m in PAPER_LABEL_RE.finditer(text):
            warnings.append(f'{path}:{s["line"]}: bare paper reference {m.group(0)!r}: the reader cannot see the paper. '
                            f'State what it says, link an anchor on this site, and keep the label only inside '
                            f'<span class="paper-ref">')
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
        if any(line.strip() for line in code_lines):
            raise BuildError(f'{doc_path}: no section has data-start, so the code of {code_path} would not be shown')
        return
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


def render_html(meta, sections, template: str, assets: str) -> str:
    rows = []
    if meta.get('breadcrumbs'):
        rows.append(f'<div class="section header"><div class="docs"><nav class="breadcrumbs">'
                    f'{render_breadcrumbs(meta["breadcrumbs"])}</nav></div>'
                    f'<div class="code"></div></div>')
    for i, s in enumerate(sections):
        code = render_code(*s['code']) if s.get('code') else ''
        code_class = 'code' if code else 'code empty'
        docs_class = 'docs doc-strings' if s['attrs'].get('data-kind') == 'doc' else 'docs'
        rows.append(f'<div class="section" id="s{i}">\n'
                    f'<div class="{docs_class}"><a class="anchor" href="#s{i}">#</a>\n{s["html"]}\n</div>\n'
                    f'<div class="{code_class}">{code}</div>\n'
                    f'</div>')
    values = {'title': html.escape(meta['title']),
              'summary': html.escape(meta.get('summary', '')),
              'assets': assets,
              'sections': '\n'.join(rows)}
    return PLACEHOLDER_RE.sub(lambda m: values[m.group(1)], template)


def build_file(code_path: Path, doc_path: Path, name: str, template: str):
    meta, body, base_line = parse_front_matter(doc_path.read_text(encoding='utf-8'), doc_path)
    for key in meta:
        if key not in FRONT_MATTER_KEYS:
            raise BuildError(f'{doc_path}: unknown front matter key {key!r} (allowed: {", ".join(FRONT_MATTER_KEYS)}); '
                             f'the annotation always describes {code_path.name}, the Python file next to it')
    if not meta.get('title'):
        raise BuildError(f'{doc_path}: front matter needs a title')
    sections = parse_sections(body, doc_path, base_line)
    for s in sections:
        kind = s['attrs'].get('data-kind')
        if kind is not None and kind not in SECTION_KINDS:
            raise BuildError(f'{doc_path}:{s["line"]}: data-kind must be one of {", ".join(SECTION_KINDS)}, '
                             f'got {kind!r}')

    warnings = paper_reference_warnings(sections, doc_path)
    code = code_path.read_text(encoding='utf-8')
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise BuildError(f'{code_path}:{e.lineno}: syntax error: {e.msg}')
    warnings += code_warnings(code, code_path)
    slice_code(sections, code.split('\n'), doc_path, code_path)
    warnings += definition_warnings(sections, code, doc_path)
    highlighted = highlight_python(code)
    for s in sections:
        if s.get('code'):
            start, chunk = s['code']
            s['code'] = (start, highlighted[start - 1:start - 1 + len(chunk)])

    ids, links = collect_links(meta, sections, doc_path)
    assets = '../' * name.count('/') + ASSET_OUT_DIR
    return {'name': name,
            'html': render_html(meta, sections, template, assets),
            'warnings': warnings,
            'ids': ids,
            'links': links}


def find_files(package: Path):
    """
    Pair every Python file in the package with the annotation next to it, and name its HTML file by its
    path in the package. A Python file without an annotation is only a warning, so the first files can be
    built while the rest are still being written; an annotation without a Python file is an error.
    """
    if not package.is_dir():
        raise BuildError(f'{package}: not a directory; pass the package that holds the Python files')
    pairs, warnings = [], []
    for code_path in sorted(package.rglob('*.py')):
        rel = code_path.relative_to(package)
        if any(part.startswith(('.', '__pycache__')) for part in rel.parts[:-1]):
            continue
        doc_path = code_path.with_name(code_path.stem + DOC_SUFFIX)
        if not doc_path.is_file():
            warnings.append(f'{code_path}: no annotation {doc_path.name} next to it; not built')
            continue
        stem = 'index' if code_path.stem == '__init__' else code_path.stem
        pairs.append((code_path, doc_path, rel.with_name(stem).as_posix()))
    for doc_path in sorted(package.rglob('*' + DOC_SUFFIX)):
        code_path = doc_path.with_name(doc_path.name[:-len(DOC_SUFFIX)] + '.py')
        if not code_path.is_file():
            raise BuildError(f'{doc_path}: no Python file {code_path.name} next to it; '
                             f'every annotation describes the Python file with the same name')
    return pairs, warnings


def collect_links(meta, sections, doc_path: Path):
    """Element ids a link can target in this file, and every href in its prose and breadcrumbs."""
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


def check_links(built, out_dir):
    """
    Relative links must reach an HTML file in this build (and an id in it) or a file in the output
    directory. A link to a Python file that is not annotated yet is only a warning; a missing anchor in
    a file that is built is an error.
    """
    errors, warnings = [], []
    ids_by_file = {f'{f["name"]}.html': f['ids'] for f in built}
    for f in built:
        for where, href in f['links']:
            if not href or ABSOLUTE_URL_RE.match(href):
                continue
            target, _, anchor = href.partition('#')
            target = target.split('?')[0]
            target = posixpath.normpath(posixpath.join(posixpath.dirname(f['name']), target)) if target \
                else f'{f["name"]}.html'
            if target in ids_by_file:
                if anchor and anchor not in ids_by_file[target]:
                    errors.append(f'{where}: link {href!r}: {target} has no element with id {anchor!r}')
            elif out_dir is None or not (out_dir / target).exists():
                warnings.append(f'{where}: link {href!r} does not point to an HTML file in this build'
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
    parser.add_argument('paths', nargs='+', type=Path, help='the package directory, or Python files with --listing')
    parser.add_argument('--out', type=Path, help='output directory for the HTML files')
    parser.add_argument('--check', action='store_true', help='validate without writing anything')
    parser.add_argument('--listing', action='store_true', help='print Python files with line numbers')
    args = parser.parse_args()

    if args.listing:
        for path in args.paths:
            if len(args.paths) > 1:
                print(f'==> {path} <==')
            listing(path)
        return 0

    if len(args.paths) != 1:
        parser.error('pass one package directory; its HTML mirrors its layout')
    if not args.check and args.out is None:
        parser.error('--out is required unless --check or --listing is given')

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    built, errors, warnings = [], [], []
    try:
        pairs, warnings = find_files(args.paths[0])
    except BuildError as e:
        pairs, errors = [], [str(e)]
    for code_path, doc_path, name in pairs:
        try:
            f = build_file(code_path, doc_path, name, template)
            built.append(f)
            warnings.extend(f['warnings'])
        except BuildError as e:
            errors.append(str(e))
    if not errors:
        link_errors, link_warnings = check_links(built, args.out)
        errors.extend(link_errors)
        warnings.extend(link_warnings)

    for w in warnings:
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
        for f in built:
            path = args.out / f'{f["name"]}.html'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f['html'], encoding='utf-8')
            print(f'wrote {path}')
    else:
        print(f'ok: {len(built)} file(s) valid')
    return 0


if __name__ == '__main__':
    sys.exit(main())
