"""
Python syntax highlighting with the standard library.

Uses `tokenize` and emits spans with Pygments' short class names (`k`, `n`, `nf`, `o`, ...), so the
stylesheet can use the familiar token palette and the page script can find every identifier
(`.n`, `.nn`, `.nc`, `.nf`) to make it clickable. Returns one HTML string per source line, so
the build can slice the highlighted file at section boundaries.
"""

import builtins
import html
import io
import keyword
import re
import tokenize
from typing import List, Tuple

BUILTINS = set(dir(builtins))
EXCEPTIONS = {name for name in BUILTINS
              if isinstance(getattr(builtins, name), type) and issubclass(getattr(builtins, name), BaseException)}
CONSTANTS = {'True', 'False', 'None'}
WORD_OPERATORS = {'and', 'or', 'not', 'in', 'is'}
PSEUDO_BUILTINS = {'self', 'cls'}
PUNCTUATION = set('()[]{},:;')
DUNDER_RE = re.compile(r'^__\w+__$')
MAGIC_VARIABLES = {'__all__', '__annotations__', '__bases__', '__class__', '__closure__', '__code__',
                   '__defaults__', '__dict__', '__doc__', '__file__', '__func__', '__globals__',
                   '__kwdefaults__', '__module__', '__mro__', '__name__', '__objclass__', '__qualname__',
                   '__self__', '__slots__', '__weakref__'}
STRING_PREFIX_RE = re.compile(r'^([rRbBuUfF]*)(\'\'\'|"""|\'|")')

FSTRING_START = getattr(tokenize, 'FSTRING_START', None)
FSTRING_MIDDLE = getattr(tokenize, 'FSTRING_MIDDLE', None)
FSTRING_END = getattr(tokenize, 'FSTRING_END', None)
LINE_BREAKS = {tokenize.NEWLINE, tokenize.NL}
SKIPPED_TYPES = {tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER, getattr(tokenize, 'ENCODING', -1)}

Span = Tuple[str, str]


class _Classifier:
    """Tracks just enough statement context to tell definitions, imports, decorators and docstrings apart."""

    def __init__(self):
        self.prev = None
        self.last_line_end = None
        self.after_def = None
        self.import_kind = None
        self.decorator_name_pending = False
        self.fstring_depth = 0

    def name(self, s: str) -> str:
        if self.decorator_name_pending:
            return 'nd'
        if self.after_def == 'def':
            return 'fm' if DUNDER_RE.match(s) else 'nf'
        if self.after_def == 'class':
            return 'nc'
        if s in ('import', 'from'):
            return 'kn'
        if s in CONSTANTS:
            return 'kc'
        if s in WORD_OPERATORS:
            return 'ow'
        if keyword.iskeyword(s):
            return 'k'
        if self.import_kind in ('from', 'import') and s != 'as':
            return 'nn'
        if s in MAGIC_VARIABLES:
            return 'vm'
        if DUNDER_RE.match(s):
            return 'fm'
        if self.prev == '.':
            return 'n'
        if s in PSEUDO_BUILTINS:
            return 'bp'
        if s in EXCEPTIONS:
            return 'ne'
        if s in BUILTINS:
            return 'nb'
        return 'n'

    def op(self, s: str) -> str:
        if s == '@' and self.prev is None:
            return 'nd'
        if s == '.' and self.import_kind in ('from', 'import'):
            return 'nn'
        if self.fstring_depth and s in '{}':
            return 'si'
        return 'p' if s in PUNCTUATION else 'o'

    def is_docstring(self) -> bool:
        return self.prev is None and self.last_line_end in (None, ':')

    def advance(self, tok):
        t, s = tok.type, tok.string
        if t in LINE_BREAKS:
            if t == tokenize.NEWLINE:
                self.last_line_end = self.prev
            self.import_kind = None
            self.decorator_name_pending = False
            self.prev = None
            return
        if t in SKIPPED_TYPES or t == tokenize.COMMENT:
            return
        if t == FSTRING_START:
            self.fstring_depth += 1
        elif t == FSTRING_END:
            self.fstring_depth -= 1

        if t == tokenize.OP and s == '@' and self.prev is None:
            self.decorator_name_pending = True
        elif t == tokenize.NAME:
            self.decorator_name_pending = False

        if t == tokenize.NAME and s in ('def', 'class'):
            self.after_def = s
        elif t == tokenize.NAME and self.after_def:
            self.after_def = None

        if t == tokenize.NAME and s == 'from' and self.prev is None:
            self.import_kind = 'from'
        elif t == tokenize.NAME and s == 'import':
            self.import_kind = 'imported' if self.import_kind == 'from' else 'import'
        self.prev = s


def _string_spans(s: str, docstring: bool) -> List[Span]:
    """A complete string literal; f-strings are split into prefix, text and `{expression}` parts."""
    m = STRING_PREFIX_RE.match(s)
    prefix = m.group(1) if m else ''
    quote_class = 'sd' if docstring else ('s1' if m and m.group(2)[0] == "'" else 's2')
    if 'f' not in prefix.lower():
        if not prefix:
            return [(s, quote_class)]
        return [(prefix, 'sa'), (s[len(prefix):], quote_class)]

    spans = [(prefix, 'sa')]
    body = s[len(prefix):]
    i, text_start = 0, 0
    while i < len(body):
        if body.startswith('{{', i) or body.startswith('}}', i):
            i += 2
            continue
        if body[i] == '{':
            if i > text_start:
                spans.append((body[text_start:i], quote_class))
            end = _matching_brace(body, i)
            spans.append(('{', 'si'))
            spans.extend(_spans(body[i + 1:end]))
            spans.append(('}', 'si'))
            i = text_start = end + 1
            continue
        i += 1
    if text_start < len(body):
        spans.append((body[text_start:], quote_class))
    return spans


def _matching_brace(s: str, open_at: int) -> int:
    depth = 0
    for i in range(open_at, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return len(s) - 1


def _spans(code: str) -> List[Span]:
    """Split `code` into (text, class) spans that concatenate back to `code` exactly."""
    line_offsets = [0]
    for line in code.split('\n'):
        line_offsets.append(line_offsets[-1] + len(line) + 1)

    def offset(pos):
        return line_offsets[pos[0] - 1] + pos[1]

    spans: List[Span] = []
    cursor = 0
    classify = _Classifier()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type in SKIPPED_TYPES or tok.type in LINE_BREAKS:
                classify.advance(tok)
                continue
            start, end = offset(tok.start), offset(tok.end)
            if start < cursor:
                continue
            if start > cursor:
                spans.append((code[cursor:start], ''))
            text = code[start:end]
            t = tok.type
            if t == tokenize.NAME:
                spans.append((text, classify.name(text)))
            elif t == tokenize.NUMBER:
                spans.append((text, 'mi' if re.fullmatch(r'[0-9_]+|0[xXoObB][0-9a-fA-F_]+', text) else 'mf'))
            elif t == tokenize.STRING:
                spans.extend(_string_spans(text, classify.is_docstring()))
            elif t == FSTRING_START:
                prefix = re.match(r'[rRbBuUfF]*', text).group(0)
                spans.extend([(prefix, 'sa'), (text[len(prefix):], 's2')])
            elif t in (FSTRING_MIDDLE, FSTRING_END):
                spans.append((text, 's2'))
            elif t == tokenize.COMMENT:
                spans.append((text, 'c1'))
            elif t == tokenize.OP:
                spans.append((text, classify.op(text)))
            else:
                spans.append((text, ''))
            classify.advance(tok)
            cursor = end
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    if cursor < len(code):
        spans.append((code[cursor:], ''))
    return spans


def _wrap(text: str, cls: str) -> str:
    text = html.escape(text, quote=False)
    return f'<span class="{cls}">{text}</span>' if cls and text else text


def highlight_python(code: str) -> List[str]:
    """Highlight `code` and return the HTML for each line (without line breaks)."""
    lines = [[]]
    for text, cls in _spans(code):
        parts = text.split('\n')
        for k, part in enumerate(parts):
            if k:
                lines.append([])
            if part:
                lines[-1].append(_wrap(part, cls))
    return [''.join(parts) for parts in lines]
