# Annotation file format

Every Python file `<module>.py` in the package is annotated by `<module>.doc.html`, in the same
directory. The build writes `<module>.html` at the same relative path in the output directory, and
`__init__.py` becomes `index.html`: `ppo/loss.py` becomes `site/loss.html`, `ppo/gae/__init__.py`
becomes `site/gae/index.html`.

`ppo/loss.doc.html`:

```html
---
title: Proximal Policy Optimization
summary: A tested PyTorch implementation of PPO with the derivation of its clipped objective.
breadcrumbs: Overview=index.html; PPO loss=loss.html
---

<section data-start="1" data-expect="import torch">
  <h1>Proximal Policy Optimization</h1>
  <p>This is a PyTorch implementation of
     <a href="https://arxiv.org/abs/1707.06347">Proximal Policy Optimization Algorithms</a>.</p>
</section>

<section data-start="5" data-expect="class ClippedPPOLoss(nn.Module):">
  <h2>Clipped objective</h2>
  <p>...</p>
</section>

<section data-start="9" data-expect="ratio = torch.exp(log_pi - sampled_log_pi)">
  <p>The probability ratio $r_t(\theta) = \frac{\pi_\theta(a_t|s_t)}{\pi_{\theta_{old}}(a_t|s_t)}$.</p>
</section>
```

## Front matter

`key: value` lines between `---` lines at the very top of the file.

| Key | Required | Meaning |
|---|---|---|
| `title` | yes | HTML `<title>`. Also write a visible `<h1>` in the first section. |
| `summary` | no | One-sentence description of the file (meta description). |
| `breadcrumbs` | no | `Label=url; Label=url` links shown above the code, relative to this file's HTML. |

Other keys are an error. There is no key for the Python file: it is always the one next to the
annotation, with the same name.

## Sections

Everything after the front matter is a sequence of `<section>` elements. Nothing else may appear
outside them except HTML comments, and sections may not be nested.

| Attribute | Meaning |
|---|---|
| `data-start` | 1-based line of the Python file where this section's code begins. |
| `data-expect` | Text that must appear on that line (whitespace-insensitive). Required with `data-start`. |
| `data-kind` | `doc` (bright) or `note` (default, dimmer). Optional; see the writing guide. |

- A section's code runs from its `data-start` up to the line before the next section's
  `data-start` (or the end of the file). Trailing blank lines are dropped.
- `data-start` values must strictly increase, point at non-blank lines, and the first one must
  come before any non-blank line, so every line of the file is shown exactly once.
- A section without `data-start` has prose and an empty code column. Use it for long
  introductions, for theory with no code of its own (a theorem and its proof above the code that
  tests it), and for a heading that introduces several functions: put it above them, then give each
  function its own section. It can appear anywhere between other sections.
- A section can be empty (`<section data-start="44" data-expect="..."></section>`): its code is
  shown with nothing beside it. Use it for lines that the prose around them does not explain.
- An empty Python file (an empty `__init__.py`) takes only sections without `data-start`.
- Attribute values may use `"..."` or `'...'`; use single quotes when the code line contains `"`
  (or write `&quot;`). `>` and `->` inside a quoted value are fine.
- Pick `data-expect` to be distinctive: the whole statement for short lines, the start of the
  statement for long ones. `return x` on its own is a poor anchor if the file has many.

The build fails, naming the file and line, if any of these rules are broken - most usefully when
the code changed and a `data-expect` no longer matches its line.

The build also warns (and a strict build such as a CI check treats warnings as failures) when:

- a section's code contains more than one top-level function or class definition;
- a section starts between a definition's first decorator and its `def`/`class` line (start it at
  the decorator instead);
- a section that starts at a definition has no heading and follows a heading on a different
  definition, so the reader cannot tell which code the heading is for.

## Prose HTML

Write ordinary HTML: `h1`-`h4`, `p`, `ul`/`ol`, `a`, `em`/`strong`, `code`, `table`, `blockquote`.
Escape `<`, `>` and `&` in prose as `&lt;`, `&gt;`, `&amp;`.

Extra styled elements:

| Element | Use |
|---|---|
| `<aside class="note">` | Deviations from the paper, caveats, implementation tricks. |
| `<figure>` + `<figcaption>` | Diagrams. Inline `<svg>` is preferred; use `currentColor` for lines and text, and the theme's token colours for accents (`var(--hl-k)` pink, `var(--hl-nf)` orange, `var(--hl-m)` purple, `var(--hl-nb)` cyan, `var(--hl-bp)` green) so it works in light and dark mode. An SVG `<text>` containing `$...$` is moved at load time into an HTML overlay on the drawing and typeset there, anchored at the same `x`, `y` (honouring `text-anchor`, `transform`, `font-size`, `font-weight`, `fill` and `opacity`, and scaling with the drawing). The `<svg>` needs a `viewBox`; do not use `<foreignObject>`. See the writing guide for when and how to draw. |
| `data-group="a b"` on SVG elements | Makes a diagram interactive. The element belongs to the groups `a` and `b` (space-separated names, unique inside the figure). Clicking it lights up every element of the same figure that shares a group with it and dims the other grouped elements; clicking it again, outside the groups, or pressing Escape, shows the whole figure. Works on shapes, paths, `<text>` (including `$...$` labels) and `<g>`; put it on a `<g>` to group a box with its label. The whole inside of a grouped shape is clickable, also with `fill="none"`, and so is a band 10 units wide around each grouped line. Elements without `data-group` are never dimmed. See the writing guide for what to group. |
| `<details><summary>` | Long proofs or side derivations the reader can expand. |
| `class="no-math"` | On any element whose `$` signs are literal (prices, shell variables). |
| `<span class="paper-ref">` | The paper's own label for something the prose has just restated: `<span class="paper-ref">(Eq. 3 in the paper)</span>`. Shown small and dim. The only place a paper label ("Eq. 3", "Fig. 14", "Algorithm 1", "Section 3.1", "Theorem 2"...) may appear; anywhere else the build warns. |
| `id="..."` on any element | A link target. Wrap an equation, figure or list that other prose refers to: `<div id="eq-loss">$$...$$</div>`, then link it with `<a href="training.html#eq-loss">the loss</a>`. The targeted element gets an accent bar when the HTML is opened at it. Use ids that are unique in the file and descriptive (`eq-path`, `fig-mask`), not paper numbers. |

## Math

Rendered in the browser by KaTeX. Delimiters:

- inline: `$...$` or `\(...\)`
- display: `$$...$$`, `\[...\]`, `\begin{align}...\end{align}`, `\begin{align*}`,
  `\begin{equation}`, `\begin{gather}`

Inside math write `\lt` and `\gt` instead of `<` and `>`. The alignment `&` in `align` can be
written literally as long as a space, `=` or `\` follows it (`&= ...`, `& \le ...`); the browser
only reinterprets `&` followed by letters. Use `\operatorname{clip}`, `\min`, `\max`, `\mathbb{E}` rather than bare words.

Equal expressions in a file are linked automatically: if `$\hat{A}_t$` appears in two places, or inside a
larger equation, every occurrence is linked. Equations look plain; clicking a linked symbol dims
everything else and makes every occurrence glow, and clicking it again (or pressing Escape) turns the lights
back on. Expressions containing `&`, `\\`, `\left`/`\right` or environments are not linked as a
whole, but the expressions inside them are. Bare numbers and the index letters `i j k l n t T d p`
are never linked on their own, so clicking a $t$ does nothing; `$\theta$`, `$x$` and `$\gamma$`
are linked.

## Code

The build highlights the code itself (standard library `tokenize`), using Pygments' class names:
`.k` keywords, `.n` names, `.nf`/`.nc` function and class names, `.o` operators, `.m*` numbers,
`.s*` strings, and so on. Clicking any identifier in the code (`.n`, `.nn`, `.nc`, `.nf`) makes every
occurrence of that name in the file glow, the same way as equation symbols. Long lines wrap; the
line numbers are part of each line, so they stay aligned.

## Look

Dark by default, light on light-mode systems. Prose takes 40% of the width and code 60%; each
section has a top border and lights up on hover. Sections marked `data-kind="doc"` are shown in
brighter text than the default `note` sections. See the writing guide for which to use.

## Self-check

After rendering, every HTML file sets `window.annotationReport`:

```js
{ mathErrors: [{tex, message}], overflowing: [{section, tex}], unrenderedDollar: [{section, text}],
  svgPlainMath: [{section, text}], svgLowContrast: [{section, text, contrast}],
  svgMisplaced: [{section, text, problem}], ok: true|false }
```

and shows a red banner when anything is wrong. `overflowing` lists display equations wider than
their column; split them over the lines of an `align*`. `svgPlainMath` lists diagram labels that look like math (LaTeX `_`, `^` or `\` outside
`$...$`, or Unicode sub/superscripts) but are not typeset; wrap them in `$...$`. `svgLowContrast` lists
diagram text and math labels with less than 3:1 contrast against the background in the current
colour scheme, usually a hard-coded dark fill seen in dark mode; it only sees the scheme it is
rendered in, so check both. `svgMisplaced` lists diagram labels whose typeset math is drawn away
from the label, or labels that stick out of their drawing. `unrenderedDollar` lists sections whose
visible text still contains `$`, usually an unbalanced delimiter (wrap literal dollar signs in
`class="no-math"`).

## Links

The build checks every relative `href` in the prose and breadcrumbs. Links are relative to the
file's own HTML, which mirrors the package: from `loss.html`, the file `gae/advantage.py` is
`gae/advantage.html`; from there, the overview is `../index.html`. A link must point to an HTML
file of the same build (`adam.html`), optionally with a section anchor or element id that exists in
it (`adam.html#s4`), to a file that exists in the output directory, or to an anchor in the same file
(`#s2`). Absolute URLs are not checked. A missing anchor in a built file is an error. A link to a
Python file that is not annotated yet is a warning, and so is the Python file itself, so you can
build the first files while the others are still unwritten. The final build must have no warnings.

## Build commands

```bash
python <skill>/scripts/build.py --listing pkg/module.py
python <skill>/scripts/build.py pkg --check
python <skill>/scripts/build.py pkg --out site
```

The build takes the package directory and annotates every `.py` file under it, in subpackages too.
Section `i` (0-based, in file order) gets the anchor `#s<i>`. The build copies `style.css` and
`annotate.js` into `<out>/assets/`.
