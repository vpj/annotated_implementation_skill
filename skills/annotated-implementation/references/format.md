# Annotation file format

An annotation file is `<page>.doc.html`. It becomes `<page>.html` in the output directory.

```html
---
title: Proximal Policy Optimization
summary: A tested PyTorch implementation of PPO with the derivation of its clipped objective.
code: ../ppo/loss.py
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
| `title` | yes | Page `<title>`. Also write a visible `<h1>` in the first section. |
| `summary` | no | One-sentence page description (meta description). |
| `code` | no | Python file this page annotates, relative to the annotation file. Omit for prose-only pages such as an overview. |
| `breadcrumbs` | no | `Label=url; Label=url` links shown above the page. |

## Sections

Everything after the front matter is a sequence of `<section>` elements. Nothing else may appear
outside them except HTML comments, and sections may not be nested.

| Attribute | Meaning |
|---|---|
| `data-start` | 1-based line of the code file where this section's code begins. |
| `data-expect` | Text that must appear on that line (whitespace-insensitive). Required with `data-start`. |
| `data-kind` | `doc` (bright) or `note` (default, dimmer). Optional; see the writing guide. |

- A section's code runs from its `data-start` up to the line before the next section's
  `data-start` (or the end of the file). Trailing blank lines are dropped.
- `data-start` values must strictly increase, point at non-blank lines, and the first one must
  come before any non-blank line, so every line of the file is shown exactly once.
- A section without `data-start` has prose and an empty code column. Use it for long
  introductions or for prose-only pages (no `code:` in the front matter).
- Attribute values may use `"..."` or `'...'`; use single quotes when the code line contains `"`
  (or write `&quot;`). `>` and `->` inside a quoted value are fine.
- Pick `data-expect` to be distinctive: the whole statement for short lines, the start of the
  statement for long ones. `return x` on its own is a poor anchor if the file has many.

The build fails, naming the file and line, if any of these rules are broken - most usefully when
the code changed and a `data-expect` no longer matches its line.

## Prose HTML

Write ordinary HTML: `h1`-`h4`, `p`, `ul`/`ol`, `a`, `em`/`strong`, `code`, `table`, `blockquote`.
Escape `<`, `>` and `&` in prose as `&lt;`, `&gt;`, `&amp;`.

Extra styled elements:

| Element | Use |
|---|---|
| `<aside class="note">` | Deviations from the paper, caveats, implementation tricks. |
| `<figure>` + `<figcaption>` | Diagrams. Inline `<svg>` is preferred; use `currentColor` for lines and text, and the theme's token colours for accents (`var(--hl-k)` pink, `var(--hl-nf)` orange, `var(--hl-m)` purple, `var(--hl-nb)` cyan, `var(--hl-bp)` green) so it works in light and dark mode. |
| `<details><summary>` | Long proofs or side derivations the reader can expand. |
| `class="no-math"` | On any element whose `$` signs are literal (prices, shell variables). |

## Math

Rendered in the browser by KaTeX. Delimiters:

- inline: `$...$` or `\(...\)`
- display: `$$...$$`, `\[...\]`, `\begin{align}...\end{align}`, `\begin{align*}`,
  `\begin{equation}`, `\begin{gather}`

Inside math write `\lt` and `\gt` instead of `<` and `>`. The alignment `&` in `align` can be
written literally as long as a space, `=` or `\` follows it (`&= ...`, `& \le ...`); the browser
only reinterprets `&` followed by letters. Use `\operatorname{clip}`, `\min`, `\max`, `\mathbb{E}` rather than bare words.

Equal expressions are linked automatically: if `$\hat{A}_t$` appears in two places, or inside a
larger equation, every occurrence is linked. Equations look plain; clicking a linked symbol dims
the page and makes every occurrence glow, and clicking it again (or pressing Escape) turns the lights
back on. Expressions containing `&`, `\\`, `\left`/`\right` or environments are not linked as a
whole, but the expressions inside them are. Bare numbers and the index letters `i j k l n t T d p`
are never linked on their own, so clicking a $t$ does nothing; `$\theta$`, `$x$` and `$\gamma$`
are linked.

## Code

The build highlights the code itself (standard library `tokenize`), using Pygments' class names:
`.k` keywords, `.n` names, `.nf`/`.nc` function and class names, `.o` operators, `.m*` numbers,
`.s*` strings, and so on. Clicking any identifier in the code (`.n`, `.nn`, `.nc`, `.nf`) makes every
occurrence of that name on the page glow, the same way as equation symbols. Long lines wrap; the
line numbers are part of each line, so they stay aligned.

## Look

Dark by default, light on light-mode systems. Prose takes 40% of the width and code 60%; each
section has a top border and lights up on hover. Sections marked `data-kind="doc"` are shown in
brighter text than the default `note` sections; all sections of prose-only pages are bright. See
the writing guide for which to use.

## Page self-check

After rendering, every page sets `window.annotationReport`:

```js
{ mathErrors: [{tex, message}], overflowing: [{section, tex}], unrenderedDollar: [{section, text}], ok: true|false }
```

and shows a red banner when anything is wrong. `overflowing` lists display equations wider than
their column; split them over the lines of an `align*`. `unrenderedDollar` lists sections whose
visible text still contains `$`, usually an unbalanced delimiter (wrap literal dollar signs in
`class="no-math"`).

## Links

The build checks every relative `href` in the prose and breadcrumbs. A link must point to a page in
the same build (`adam.html`), optionally with a section anchor or element id that exists on it
(`adam.html#s4`), to a file that exists in the output directory, or to an anchor on the same page
(`#s2`). Absolute URLs are not checked. A missing anchor on a built page is an error; a link to a
page that is not in the build is a warning, so you can build the first pages while the others are
still unwritten. The final build of all pages must have no warnings.

## Build commands

```bash
python <skill>/scripts/build.py --listing pkg/module.py
python <skill>/scripts/build.py annotations/*.doc.html --check
python <skill>/scripts/build.py annotations/*.doc.html --out site
```

All pages go flat into `--out`; link between them with relative URLs (`loss.html#s3`). Section
`i` (0-based, in file order) gets the anchor `#s<i>`. The build copies `style.css` and
`annotate.js` into `<out>/assets/`.
