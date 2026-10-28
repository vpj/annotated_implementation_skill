# Writing guide

The goal is an annotated file a reader can study top to bottom and come away able to re-derive the method
and re-write the code. Every section answers "what is this line doing, and why does the paper
want it?"

## Kinds of files

The code is the subject; the writing exists to explain it. Every explanation sits next to the code
it explains, in the annotation of the Python file that contains that code.

**`__init__.py`** (the package overview)
- One section at line 1, beside the imports that export the main classes.
- `<h1>` with the method's name.
- First paragraph: "This is a [PyTorch](https://pytorch.org) implementation of
  [<paper title>](<arXiv abs URL>)." Then a short description of what the paper does.
- A link to every other file with one line on what it implements.
- If the method builds on other papers implemented here, say so and link their files.
- Nothing else: derivations, figures and results belong in the other files, beside their code.

**Module** (one Python file: a model, loss, algorithm, or the helpers they use)
- `<h1>` + paper link + the introduction to this file's code, above the imports.
- An `<h2>` section per class or top-level function, above its definition, containing the
  derivation or equations it implements.
- `<h3>` for methods that need their own explanation (`forward`, `__call__`, a sampling step).
- `<h4>` for named sub-steps inside a method.

**Experiment** (the experiment's own file, e.g. `experiment.py`)
- What is trained on what, and what result to expect (numbers, curves, time on what hardware).
- Configuration values explained where they are set, especially ones that differ from the paper.

**Theory** (a theorem, a proof, a convergence analysis)
- It goes in the file whose code it is about, in sections without `data-start` above that code.
- When the paper's claim can be shown by running something (a counterexample, a toy problem where
  the bound is tight), write that code as a file of the package and put the theory in its
  annotation.

## Section granularity

Choose split points so each section's prose explains exactly the code beside it.

- Start a section at every class and function definition. The build warns when a section covers
  more than one top-level definition.
- A heading names only the code in its own section. When one heading introduces several functions
  (four weight functions, two helpers for one derivation), put the heading and the shared
  explanation in a section **without** `data-start`, above the functions, and give each function
  its own short section below it. Better still, when the functions belong together, group them in a
  class and put the heading on the class. The build warns when a definition without a heading sits
  under the heading of a different definition.
- Inside a function, start a section at each step that corresponds to an equation or a decision
  in the paper. A one-line section showing the equation that line computes is the most useful
  kind:
  - prose: `$\delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$`
  - code: `delta = rewards[:, t] + gamma * last_value - values[:, t]`
- Do not split off trivial lines (assignments of constructor arguments, `return x`); let them ride
  with the section above. A section with no prose is better merged.
- Put long derivations above the class or function they justify, not inside a method.

## Doc sections and notes

Each section is either a **doc** (`data-kind="doc"`, shown in brighter text) or a **note** (the
default, dimmer). The contrast lets a reader skim the main explanation and drop into the notes
only where they want detail. Decide per section:

- `doc`: the file's introduction, the explanation of a class or function, a derivation or proof,
  anything that explains *why* the method works, and notes that correct the paper.
- `note`: a short remark on the line beside it, such as the equation a line computes, a default
  value, a shape, or a step counter.

A section with a heading is usually a doc, but not always: a `###` that only names a method
(“Update one parameter”) with no explanation under it can stay a note. Most files end up with
a few doc sections carrying the narrative and many short notes.

## Math

- Define every symbol the first time it appears: "where $r$ is the reward, $\gamma \in [0, 1]$ is
  the discount factor".
- "First" means first from the top of the file, not next to the code that makes the value. A
  section without code near the top (results, an overview) must define every symbol and setting it
  uses, also when a code section further down defines it again. Before you build, read the file
  from the top. For each symbol and setting name ($\sigma$, $k$, $G$, `max_tokens`), find its first
  occurrence and make sure the definition is there.
- **Write each symbol identically everywhere in the file.** Clicking a symbol highlights every
  equal expression in the file, so `\hat{A}_t` here and `\hat A_t` there breaks
  the link. Decide notation once (match the paper unless it clashes with the code) and keep it.
- Make the prose math match the code: if the code normalizes the advantage, say so and show
  $\bar{A}_t = \frac{\hat{A}_t - \mu(\hat{A})}{\sigma(\hat{A})}$ where the normalization happens.
- Use `align*` for multi-step derivations, one step per line, so each transformation is visible.
  Use numbered `align` only when the prose refers to an equation by number; the prose column is
  narrow and numbers collide with long lines.
- Write scripted symbols with the subscript before the superscript (`\hat{A}_t^{(k)}`); the same
  base symbol is then still linked where it appears without the superscript.
  Between steps, add a sentence when the step is not obvious ("importance sampling $a$ from
  $\pi_{\theta_{old}}$").
- Use `\operatorname{clip}`, `\min`, `\max`, `\mathbb{E}`, `\log`, never bare words in math.
- Keep display equations narrow. The prose column is only 40% of the width, about 365-485px of text
  on a desktop screen, which fits roughly 35 characters of LaTeX source per line for ordinary
  expressions (fewer with fractions and sums). Notes (`aside.note`) are narrower still. Split anything longer over the lines of an `align*`: a long right-hand side on lines
  starting with `&=`, or a sum of large terms on lines starting with `& +`.
- Name a new quantity with a new symbol. If a derivation needs a ratio that looks like one from the
  paper but is not the same (for example $\beta_1^2 / \beta_2$ versus the paper's
  $\gamma = \beta_1^2 / \sqrt{\beta_2}$), give it its own letter; reusing the paper's would link two
  different things, so clicking one would highlight the other.
- Every number in the prose (a ratio, a bound at the default hyperparameters, how many times too
  large something is) must come from a calculation you ran, not an estimate.

## Derivations and proofs

Follow the depth the user chose:

- **Intuition**: state the result, explain in words why it is reasonable, link the paper section.
- **Derivation**: every algebraic step from the starting objective to what the code computes.
  Name the assumptions where they are made ("we assume $d^{\pi_\theta}$ and $d^{\pi_{\theta_{old}}}$
  are close; the error is bounded by their KL divergence").
- **Proof**: the full argument, with the paper's equation and theorem numbers referenced. Put long
  proofs in `<details><summary>Proof</summary>...</details>` so the main flow stays readable.
- When skipping a proof, link it and say what it shows.

## Language: Simplified Technical English

Write all prose in [ASD-STE100 Simplified Technical English](https://www.asd-ste100.org/).
Readers of these files are often not native English speakers, and they read slowly, next to math
and code. Simple, regular sentences let them spend their attention on the method.

**Sentences**
- Descriptive sentences have at most 25 words. Instructions ("Run...", "Set...") have at most 20.
- One topic per sentence. Split "A, and B, so C" into two or three sentences.
- Paragraphs have at most six sentences and one topic.
- Use the active voice: "The sampler logs the top-$k$ log-probabilities", not "The top-$k$
  log-probabilities are logged".
- Use simple tenses: present for what the method does, past for what an experiment measured.
- Put a condition first: "If $p = q$, the correction is zero."
- Use a vertical list for steps, conditions or more than two parallel items.

**Words**
- Use simple, common words, each with one meaning: "use", not "leverage"; "show", not
  "demonstrate"; "start", not "kick off"; "about", not "roughly speaking".
- No phrasal verbs ("set up", "carry out", "end up"), no idioms and no metaphors ("with nothing to
  hide behind", "the trainer chases the sampler"). Say what happens.
- Use one term for one thing in every file. If it is the "sampler", it is never also "the inference
  engine" or "the generator".
- Keep the articles: "the gradient of the loss", not "gradient of loss".
- At most three nouns in a row: "the tail mass of the sampler", not "sampler tail mass ratio".
- Avoid "-ing" words as nouns or adjectives where a simple verb works: "When you clip the ratio",
  not "Clipping the ratio".
- No contractions.
- Technical names (policy gradient, logits, importance sampling, KL divergence) and the names in the
  code are allowed. Define each one the first time it appears.

**Example**

Before: "Distilling towards a fixed teacher would converge. Here the sampler is a biased copy of the
trainer and is re-copied after every step, so the trainer chases a target that moves with it."

After: "Distillation to a fixed teacher converges. Here, the sampler is a copy of the trainer with
an error. After each step, the sampler gets the new weights of the trainer. Thus the target moves
with the trainer, and the error has an effect at each step."

**Content**
- Explain **why**, not what. "Clip the ratio" restates the code. "The minimum stops the gradient
  when the ratio is outside $[1 - \epsilon, 1 + \epsilon]$. This prevents a large change to the
  policy in one update" explains it.
- Say what the trade-offs and uncertainties are: "This adds bias. It also makes the variance much
  smaller." "The paper does not give this value. We use 0.95."
- Use "we" only for decisions in the implementation ("We use 0.2"). Describe the method directly:
  "The trainer computes...", not "We compute...".
- Mark every deviation from the paper with `<aside class="note">`.
- When a test showed that a claim in the paper is wrong or loose, say so in a note next to the code
  the claim is about: what the paper states, a short derivation of the correct statement, the input
  that breaks the original (usually the equality case of the inequality used), and the value the
  implementation actually produced. Keep the tone factual; the point is the correct statement, not
  the error. If the paper's claim holds for typical inputs, say that too.
- When a published result (a proof, a theorem) is known to be wrong, cite the work that showed it,
  explain where the argument fails, and back it with a test if the failure can be reproduced.
- No filler ("In this section we will...", "This file implements..."), no marketing words, no
  emojis. The annotation does not narrate itself. Say the thing directly.

## Diagrams

A reader re-deriving a method from the annotation needs pictures as much as equations. Plan the
diagrams with the file plan, and expect most files to have at least one.

**When to draw.** Whenever a reader would otherwise build the picture in their head:

- **Structure:** what goes into a model and what comes out, how two models differ (one row
  each), which modules are new and which are reused.
- **Tensors and tokens:** the token sequence a transformer sees, tensor shapes through a block,
  how a trajectory is cut into chunks.
- **Masks and matrices:** an attention mask, a transition matrix, a covariance pattern. Draw the
  grid; it is far clearer than prose rules.
- **Time:** a training or control loop, a timeline of rollouts and updates, what happens at each
  step of a sampler, what is cached and what is thrown away.
- **Distributions and geometry:** a sampling density, the region of input space a schedule
  covers, a probability path, a clipped objective as a function of the ratio. When a derivation
  claims "the density is concentrated near 0" or "it only covers the diagonal", plot it.
- **Before and after:** the paper's choice against the alternative it replaces.

Skip diagrams that only restate one equation or that decorate.

**How to draw.**

- Inline `<svg>` inside a `<figure>` with a `<figcaption>` that says what to notice, not just what
  it is. Give the figure an `id` (`fig-mask`) so other prose can link to it.
- Keep it small: a `viewBox` around 400 wide for the prose column, `width="100%"`, font size 11 to 13 in viewBox units.
- Use `currentColor` for lines and text and the theme's token colours (`var(--hl-k)` pink,
  `var(--hl-nf)` orange, `var(--hl-m)` purple, `var(--hl-nb)` cyan, `var(--hl-bp)` green) for
  accents, so it works in both colour schemes. Use the same colour for the same kind of thing
  across a file's figures, and say what each colour means in the caption.
- **SVG text is black unless told otherwise.** `<text>` takes its colour from `fill`, whose default
  is black, not from the CSS `color` that `currentColor` follows; math labels inherit that fill.
  Put `fill="currentColor"` on the `<svg>` element (and `fill="none"` on any outline-only shape),
  or on every `<text>`. Never hard-code `black`, `white` or a grey hex for text or lines. The
  stylesheet defaults unfilled figure text to `currentColor`, but a figure copied elsewhere or
  saved as a standalone `.svg` does not get that rule.
- **Math in labels:** write a label containing math as LaTeX in `$...$`, exactly as the prose
  writes it: `<text x="60" y="55" text-anchor="middle">$o_l$, $c$, $q_l$</text>`. The browser
  replaces it with a typeset label at the same anchor point, and because the LaTeX is identical
  to the prose, clicking the symbol in the figure lights up the prose and equations too. Never fake
  math with Unicode subscripts (`oₗ`) or plain `o_l`; the self-check reports both.
- Never put HTML in the SVG yourself (`<foreignObject>`). WebKit (Safari) positions HTML inside it
  without the SVG's offset and scaling, and KaTeX is built from positioned boxes, so math drawn
  that way lands far from its label in Safari while looking right in Chrome. A `$...$` label in a
  plain `<text>` avoids this: `annotate.js` moves it into an HTML overlay on top of the drawing. The
  `<svg>` needs a `viewBox`.
- Labels with math are taller than plain text; leave at least one font size of space around them.
- **Generate figures that show data or code behaviour.** When a figure shows what the code
  computes (an attention mask, a schedule's density, a sampled trajectory), write a small script
  that calls the implementation and emits the SVG, and keep it in the project (for example
  `scripts/figures.py`). Mark the figure's place in the annotation with
  `<!-- figure:name -->...<!-- /figure:name -->` and have the script rewrite what is between
  the markers. A hand-drawn copy drifts from the code; a generated one cannot.
- **Charts and tables must be readable without the prose.** Cover the text around a chart. From the
  chart and its caption only, a reader must know what each axis is, what each line or bar is, and
  which settings were used. Thus:
  - Label both axes with the quantity, and its unit if it has one: "success rate of the trainer",
    "$\lVert \theta - \theta_0 \rVert$", "training step". Tick values are not a label. Put the
    y label on the axis (rotated), not only in a panel title.
  - A panel title names the quantity or the setting of the panel. A group name only ("GRPO family")
    is not sufficient.
  - Put a legend for each colour and line style in the figure.
  - Give each fixed setting that the chart depends on (noise size, number of seeds, $k$) in the
    caption, and define its symbol there or before the figure.
  - In a table, each column header names a quantity. Define each symbol in a header in the text
    directly before the table.
  - In a chart helper in `scripts/figures.py`, name each label parameter for the axis it labels
    (`x_label`, `y_label`) and make both required, so that a chart cannot have an axis without a
    label.
- Hand-draw only conceptual figures (boxes and arrows). Lay them out on a grid in the `viewBox`
  so boxes align, and use one arrow marker defined in `<defs>`.
- **One `<path>` per arrow.** `marker-end` draws a head only at the last point of a path, so
  `d="M0 0 H10 M20 0 H30"` gets one arrowhead, on the second segment. Each arrow is its own
  `<path>` (or `<line>`) with its own `marker-end`.
- Check every figure in the browser at desktop width, in both colour schemes and in both Chrome
  and WebKit: labels inside their boxes, every arrow with a head, nothing clipped, math typeset. On
  macOS, `scripts/webkit_check.swift` renders an HTML file in WebKit and saves each figure as a PNG.

## The reader does not have the paper

The annotations must make sense on their own. "Eq. 2", "Fig. 14", "Algorithm 1, line 13" or "see
Section 3.1" are meaningless to someone who has only the annotated code in front of them, and they cannot
check what the label pointed to. So:

- **Say what it is.** Instead of "this is Eq. 2", show the equation: "the noisy sample is
  $x_t = t x_1 + (1 - t) x_0$". Instead of "following Fig. 14", describe or draw the figure.
  Instead of "the paper's Table 4 shows", give the numbers and what was compared.
- **Refer within the site with links.** When prose depends on an equation, figure or step shown
  elsewhere on this site, give that element an `id` and link to it:
  `<a href="flow_matching.html#eq-path">the interpolation path</a>`. The link text names the
  thing, not its number.
- **Keep the paper's label only as a pointer for readers who open the paper.** Put it in
  `<span class="paper-ref">(Eq. 3 in the paper)</span>`, right beside the content it labels. Never
  let the label carry meaning that the surrounding prose does not.
- **Discrepancies inside the paper** ("the algorithm box samples $t \sim \operatorname{Beta}(7, 1)$
  but the text uses $1 - \eta$") are described by their content on both sides, with paper-ref
  labels for each.
- **Pseudocode.** If the paper's algorithm box is central, reproduce its steps in the annotation (an
  `<ol>` with an `id`) and refer to steps by linking that list, not "line 13".

The build warns about every paper label outside a `paper-ref` span, so an annotation that still leans on
the paper's numbering does not pass.

## Links

- Paper: arXiv abstract URL (`https://arxiv.org/abs/<id>`), not the PDF.
- Within the site: link anchors on elements (`training.html#eq-flash`), never the paper's numbers.
- Other files: relative to this file's HTML, which mirrors the package (`gae.html`,
  `loss.html#s4`, `../index.html`).
- Prior work the reader may need: link the paper, or its file here if implemented.
