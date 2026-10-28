"""
Line charts and result records for annotation files, with the standard library only.

Copy this file into the project's `scripts/` folder and import it from `scripts/figures.py`. The
layout numbers and checks here are the rules in `references/figures.md`; change them here, not in
each figure.

    import charts

    records = charts.load_records(ROOT / 'experiments' / 'results' / 'convergence.json')
    adam = charts.Line(charts.mean_curve(records, 'loss', method='adam'), charts.COLORS[0])
    adamax = charts.Line(charts.mean_curve(records, 'loss', method='adamax'), charts.COLORS[1])
    steps = charts.mean_curve(records, 'step', method='adam')
    body = charts.panel(0, 400, 170, [adam, adamax], steps, 'training loss, 3 seeds',
                        x_label='step', y_label='loss', y_range=(0, 2))
    body += charts.legend([('Adam', adam), ('AdaMax', adamax)], y=186)
    figure = charts.svg(400, 196, 'Training loss of Adam and AdaMax', body)

    charts.replace_markers(ROOT.glob('adam/*.doc.html'), {'convergence': lambda: figure})
"""

from __future__ import annotations

import html
import json
import math
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

COLORS = ['var(--hl-nb)', 'var(--hl-k)', 'var(--hl-nf)', 'var(--hl-m)', 'var(--hl-bp)']

TITLE_SIZE = 12
LEGEND_SIZE = 11
LABEL_SIZE = 10
MARGIN_LEFT, MARGIN_TOP, MARGIN_BOTTOM, MARGIN_RIGHT = 46, 22, 26, 14
LEGEND_ROW = 18
MAX_COLORS = 5
CHAR_WIDTH = 0.6


@dataclass
class Line:
    values: list[float]
    color: str
    dashed: bool = False
    band: tuple[list[float], list[float]] | None = None


def write_records(path: Path, records: list[dict], settings: dict) -> None:
    """Save runs as {"settings": {...}, "records": [{<fields>, "values": {name: [...]}}, ...]}."""
    for record in records:
        if 'values' not in record:
            raise ValueError(f'record without "values": {sorted(record)}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'settings': settings, 'records': records}, separators=(',', ':')))
    print(f'{path}: {len(records)} records, {path.stat().st_size / 1e6:.2f} MB')


def load_records(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text())['records']


def select(records: list[dict], **fields) -> list[dict]:
    """The records whose fields equal all of `fields` exactly. Raises if there are none."""
    chosen = [r for r in records if all(r.get(k) == v for k, v in fields.items())]
    if not chosen:
        raise KeyError(f'no record has {fields}')
    return chosen


def _curves(records: list[dict], field: str, fields: dict) -> list[list[float]]:
    curves = [r['values'][field] for r in select(records, **fields)]
    if len({len(c) for c in curves}) != 1:
        raise ValueError(f'records with {fields} have {field} curves of different lengths')
    return curves


def mean_curve(records: list[dict], field: str, **fields) -> list[float]:
    """The mean over the matching records (usually the seeds) of one recorded quantity."""
    curves = _curves(records, field, fields)
    return [sum(values) / len(values) for values in zip(*curves)]


def spread(records: list[dict], field: str, **fields) -> tuple[list[float], list[float]]:
    """The minimum and maximum over the matching records, for `Line.band`."""
    curves = _curves(records, field, fields)
    return [min(values) for values in zip(*curves)], [max(values) for values in zip(*curves)]


def _escape(text: str) -> str:
    """Escape text for SVG. `$...$` math is unchanged by this, and the browser unescapes it before KaTeX."""
    return html.escape(text, quote=True)


def svg(width: float, height: float, label: str, body: str) -> str:
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" fill="currentColor" role="img" '
        f'aria-label="{_escape(label)}">{body}</svg>'
    )


def _text_width(text: str, size: float) -> float:
    """Rough width of a label; a LaTeX command counts as one character."""
    plain = re.sub(r'\\[A-Za-z]+', 'x', text).replace('$', '').replace('{', '').replace('}', '')
    return len(plain) * size * CHAR_WIDTH


def _ticks(lo: float, hi: float, log: bool) -> list[float]:
    if log:
        ticks = [10.0**e for e in range(math.ceil(math.log10(lo)), math.floor(math.log10(hi)) + 1)]
        if not ticks:
            raise ValueError(f'a log axis from {lo:g} to {hi:g} has no power of 10 to label; '
                             f'widen y_range to a power of 10 or use a linear axis')
        return ticks
    return [lo, (lo + hi) / 2, hi]


def _check_range(title: str, values: list[float], y_range: tuple[float, float]) -> None:
    """A value outside y_range would be drawn flat along the edge, where it looks like real data."""
    y_min, y_max = y_range
    tolerance = 1e-9 * (y_max - y_min)
    outside = [v for v in values if not y_min - tolerance <= v <= y_max + tolerance]
    if outside:
        raise ValueError(f'{title}: values from {min(outside):g} to {max(outside):g} are outside '
                         f'y_range {y_range}; choose a range that holds the quantity')


def _tick_label(value: float, log: bool) -> str:
    return f'1e{round(math.log10(value))}' if log else f'{value:g}'


def panel(
    x0: float,
    width: float,
    height: float,
    lines: list[Line],
    steps: list[float],
    title: str,
    *,
    x_label: str,
    y_label: str,
    y_range: tuple[float, float],
    log: bool = False,
    every: int = 1,
) -> str:
    """One set of axes at horizontal offset x0. `steps` are the x values shared by all lines."""
    if not lines:
        raise ValueError(f'{title}: a panel needs at least one line')
    colors = [line.color for line in lines]
    if len(set(colors)) > MAX_COLORS:
        raise ValueError(f'{title}: {len(set(colors))} colours; use at most {MAX_COLORS} in a panel')
    for color in set(colors):
        styles = [line.dashed for line in lines if line.color == color]
        if len(styles) != len(set(styles)):
            raise ValueError(f'{title}: two lines with colour {color} and the same dash; the reader cannot tell them apart')
    if len(steps) < 2 or steps[-1] == steps[0]:
        raise ValueError(f'{title}: a line chart needs at least two different steps, got {list(steps)}')
    for line in lines:
        if len(line.values) != len(steps):
            raise ValueError(f'{title}: a line has {len(line.values)} values for {len(steps)} steps')
        _check_range(title, line.values, y_range)
        if line.band is not None:
            _check_range(title, line.band[0] + line.band[1], y_range)
    plot_w = width - MARGIN_LEFT - MARGIN_RIGHT
    plot_h = height - MARGIN_TOP - MARGIN_BOTTOM
    if _text_width(y_label, LABEL_SIZE) > plot_h:
        raise ValueError(f'y label "{y_label}" is longer than the plot; use a symbol and define it in the caption')
    if _text_width(title, TITLE_SIZE) > width:
        raise ValueError(f'title "{title}" is wider than the panel')

    y_min, y_max = y_range
    if log and y_min <= 0:
        raise ValueError(f'{title}: a log axis needs y_range[0] > 0')
    fy = (lambda v: math.log10(max(v, y_min))) if log else (lambda v: v)
    lo, hi = fy(y_min), fy(y_max)
    left, right = x0 + MARGIN_LEFT, x0 + MARGIN_LEFT + plot_w
    bottom = MARGIN_TOP + plot_h
    X = lambda s: left + plot_w * (s - steps[0]) / (steps[-1] - steps[0])
    Y = lambda v: MARGIN_TOP + plot_h * (1 - (min(max(fy(v), lo), hi) - lo) / (hi - lo))

    parts = [
        f'<text x="{left + plot_w / 2}" y="12" text-anchor="middle" font-size="{TITLE_SIZE}">{_escape(title)}</text>',
        f'<line x1="{left}" x2="{right}" y1="{bottom}" y2="{bottom}" stroke="currentColor" stroke-opacity="0.5"/>',
        f'<line x1="{left}" x2="{left}" y1="{MARGIN_TOP}" y2="{bottom}" stroke="currentColor" stroke-opacity="0.5"/>',
    ]
    for t in _ticks(y_min, y_max, log):
        parts.append(
            f'<text x="{left - 4}" y="{Y(t) + 4:.1f}" text-anchor="end" '
            f'font-size="{LABEL_SIZE}">{_tick_label(t, log)}</text>'
        )
    middle = float(f'{(steps[0] + steps[-1]) / 2:.2g}')
    for s in (steps[0], middle, steps[-1]):
        parts.append(
            f'<text x="{X(s):.1f}" y="{bottom + 13}" text-anchor="middle" font-size="{LABEL_SIZE}">{s:g}</text>'
        )
    parts.append(
        f'<text x="{left + plot_w / 2}" y="{height - 2}" text-anchor="middle" '
        f'font-size="{LABEL_SIZE}">{_escape(x_label)}</text>'
    )
    y_mid = MARGIN_TOP + plot_h / 2
    parts.append(
        f'<text x="{x0 + 10}" y="{y_mid}" text-anchor="middle" font-size="{LABEL_SIZE}" '
        f'transform="rotate(-90 {x0 + 10} {y_mid})">{_escape(y_label)}</text>'
    )

    keep = [i for i in range(len(steps)) if i % every == 0 or i == len(steps) - 1]
    for line in lines:
        if line.band is not None:
            low, high = line.band
            outline = [(X(steps[i]), Y(high[i])) for i in keep] + [(X(steps[i]), Y(low[i])) for i in reversed(keep)]
            points = ' '.join(f'{x:.1f},{y:.1f}' for x, y in outline)
            parts.append(f'<polygon points="{points}" fill="{line.color}" fill-opacity="0.15" stroke="none"/>')
        points = ' '.join(f'{X(steps[i]):.1f},{Y(line.values[i]):.1f}' for i in keep)
        dash = ' stroke-dasharray="5 3"' if line.dashed else ''
        parts.append(f'<polyline points="{points}" fill="none" stroke="{line.color}" stroke-width="1.8"{dash}/>')
    return ''.join(parts)


def legend(
    items: list[tuple[str, Line]],
    y: float,
    x0: float = MARGIN_LEFT,
    spacing: float = 74,
    width: float = 400,
) -> str:
    """One row of line samples under the panels, in an svg `width` wide. Each further row goes LEGEND_ROW lower."""
    parts = []
    for n, (label, line) in enumerate(items):
        x = x0 + n * spacing
        if n + 1 < len(items) and _text_width(label, LEGEND_SIZE) + 24 > spacing:
            raise ValueError(f'legend label "{label}" is wider than the spacing {spacing}')
        if x + 20 + _text_width(label, LEGEND_SIZE) > width:
            raise ValueError(f'legend label "{label}" runs past the right edge ({width}); '
                             f'use a smaller spacing or a second row')
        dash = ' stroke-dasharray="5 3"' if line.dashed else ''
        parts.append(
            f'<line x1="{x}" x2="{x + 16}" y1="{y}" y2="{y}" stroke="{line.color}" stroke-width="2"{dash}/>'
            f'<text x="{x + 20}" y="{y + 4}" font-size="{LEGEND_SIZE}">{_escape(label)}</text>'
        )
    return ''.join(parts)


def replace_markers(annotations: Iterable[Path], figures: dict[str, Callable[[], str]]) -> None:
    """
    Rewrite the text between <!-- figure:name --> and <!-- /figure:name --> in each annotation file.
    Only files that have markers are written.
    """
    found = set()
    for path in annotations:
        text = path.read_text()
        opening = re.findall(r'<!-- figure:([\w-]+) -->', text)
        closing = re.findall(r'<!-- /figure:([\w-]+) -->', text)
        for name in sorted(set(closing) - set(opening)):
            raise SystemExit(f'{path.name}: closing marker /figure:{name} has no opening marker')
        if not opening:
            continue
        for name in opening:
            if name not in figures:
                raise SystemExit(f'{path.name}: marker figure:{name} has no figure function')
            pattern = re.compile(rf'(<!-- figure:{name} -->).*?(<!-- /figure:{name} -->)', re.S)
            if not pattern.search(text):
                raise SystemExit(f'{path.name}: figure:{name} has no closing marker')
            content = figures[name]()
            text = pattern.sub(lambda m: m.group(1) + '\n' + content + '\n' + m.group(2), text)
            found.add(name)
            print(f'{path.name}: {name}')
        path.write_text(text)
    missing = sorted(set(figures) - found)
    if missing:
        raise SystemExit(f'no annotation file has a marker for: {", ".join(missing)}')
