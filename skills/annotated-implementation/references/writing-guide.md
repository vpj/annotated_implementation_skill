# Writing guide

The goal is a page a reader can study top to bottom and come away able to re-derive the method
and re-write the code. Every section answers "what is this line doing, and why does the paper
want it?"

## Page types

**Overview page** (usually prose only, or annotating the package's `__init__.py`)
- `<h1>` with the method's name.
- First paragraph: "This is a [PyTorch](https://pytorch.org) implementation of
  [<paper title>](<arXiv abs URL>)." Then one paragraph of intuition: what problem the method
  solves, what was wrong with what came before, and the one key idea.
- Links to every other page with one line each on what it covers.
- If the method builds on other papers implemented here, say so and link those pages.

**Component page** (a model, loss, algorithm)
- `<h1>` + paper link + one or two paragraphs of context, above the imports.
- An `<h2>` section per class or top-level function, above its definition, containing the
  derivation or equations it implements.
- `<h3>` for methods that need their own explanation (`forward`, `__call__`, a sampling step).
- `<h4>` for named sub-steps inside a method.

**Experiment page**
- What is trained on what, and what result to expect (numbers, curves, time on what hardware).
- Configuration values explained where they are set, especially ones that differ from the paper.

## Section granularity

Choose split points so each section's prose explains exactly the code beside it.

- Start a section at every class and function definition.
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

- `doc`: the page introduction, the explanation of a class or function, a derivation or proof,
  anything that explains *why* the method works, and notes that correct the paper.
- `note`: a short remark on the line beside it, such as the equation a line computes, a default
  value, a shape, or a step counter.

A section with a heading is usually a doc, but not always: a `###` that only names a method
(“Update one parameter”) with no explanation under it can stay a note. Most pages end up with
a few doc sections carrying the narrative and many short notes.

## Math

- Define every symbol the first time it appears: "where $r$ is the reward, $\gamma \in [0, 1]$ is
  the discount factor".
- **Write each symbol identically everywhere on the page.** Clicking a symbol highlights every
  equal expression on the page, so `\hat{A}_t` here and `\hat A_t` there breaks
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
- Keep display equations narrow. The prose column is only 40% of the page, about 365-485px of text
  on a desktop screen, which fits roughly 35 characters of LaTeX source per line for ordinary
  expressions (fewer with fractions and sums). Notes (`aside.note`) are narrower still. Split anything longer over the lines of an `align*`: a long right-hand side on lines
  starting with `&=`, or a sum of large terms on lines starting with `& +`. Prose-only pages are
  wider (about 800px).
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

## Voice

- Plain and direct, first person plural ("we take the minimum so that..."). Short sentences.
- Explain **why**, not what. "Clip the ratio" restates the code; "the minimum means the gradient
  only pulls $\pi_\theta$ back towards $\pi_{\theta_{old}}$ once the ratio leaves
  $[1 - \epsilon, 1 + \epsilon]$, which keeps the update from collapsing the policy" explains it.
- Be honest about trade-offs and uncertainty: "this introduces bias but reduces variance a lot",
  "the paper does not state this value; we use 0.95".
- Mark every deviation from the paper with `<aside class="note">`.
- When a test showed that a claim in the paper is wrong or loose, say so in a note next to the code
  the claim is about: what the paper states, a short derivation of the correct statement, the input
  that breaks the original (usually the equality case of the inequality used), and the value the
  implementation actually produced. Keep the tone factual; the point is the correct statement, not
  the error. If the paper's claim holds for typical inputs, say that too.
- When a published result (a proof, a theorem) is known to be wrong, cite the work that showed it,
  explain where the argument fails, and back it with a test if the failure can be reproduced.
- No filler ("In this section we will..."), no marketing words, no emojis.

## Diagrams

A reader re-deriving a method from the page needs pictures as much as equations. Plan the
diagrams with the page plan, and expect most pages to have at least one.

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
- Keep it small: a `viewBox` around 400 wide for the prose column (up to about 800 on prose-only
  pages), `width="100%"`, font size 11 to 13 in viewBox units.
- Use `currentColor` for lines and text and the theme's token colours (`var(--hl-k)` pink,
  `var(--hl-nf)` orange, `var(--hl-m)` purple, `var(--hl-nb)` cyan, `var(--hl-bp)` green) for
  accents, so it works in both colour schemes. Use the same colour for the same kind of thing
  across a page's figures, and say what each colour means in the caption.
- **Math in labels:** write a label containing math as LaTeX in `$...$`, exactly as the prose
  writes it: `<text x="60" y="55" text-anchor="middle">$o_l$, $c$, $q_l$</text>`. The page
  replaces it with a typeset label at the same anchor point, and because the LaTeX is identical
  to the prose, clicking the symbol in the figure lights up the prose and equations too. Never fake
  math with Unicode subscripts (`oₗ`) or plain `o_l`; the self-check reports both.
- Labels with math are taller than plain text; leave at least one font size of space around them.
- **Generate figures that show data or code behaviour.** When a figure shows what the code
  computes (an attention mask, a schedule's density, a sampled trajectory), write a small script
  that calls the implementation and emits the SVG, and keep it in the project (for example
  `scripts/figures.py`). Mark the figure's place in the annotation with
  `<!-- figure:name -->...<!-- /figure:name -->` and have the script rewrite what is between
  the markers. A hand-drawn copy drifts from the code; a generated one cannot.
- Hand-draw only conceptual figures (boxes and arrows). Lay them out on a grid in the `viewBox`
  so boxes align, and use one arrow marker defined in `<defs>`.
- Check every figure in the browser at desktop width: labels inside their boxes, nothing
  clipped, math typeset.

## The reader does not have the paper

The pages must make sense on their own. "Eq. 2", "Fig. 14", "Algorithm 1, line 13" or "see
Section 3.1" are meaningless to someone who has only the page in front of them, and they cannot
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
- **Pseudocode.** If the paper's algorithm box is central, reproduce its steps on the page (an
  `<ol>` with an `id`) and refer to steps by linking that list, not "line 13".

The build warns about every paper label outside a `paper-ref` span, so a page that still leans on
the paper's numbering does not pass.

## Links

- Paper: arXiv abstract URL (`https://arxiv.org/abs/<id>`), not the PDF.
- Within the site: link anchors on elements (`training.html#eq-flash`), never the paper's numbers.
- Other pages: relative (`gae.html`, `loss.html#s4`).
- Prior work the reader may need: link the paper, or its page here if implemented.
