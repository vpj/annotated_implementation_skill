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

Add one when structure is easier to see than to read: data flow through a model, tensor shapes
through a block, a timeline of rollouts and updates. Inline SVG inside `<figure>`, with a
`<figcaption>`. Use `currentColor` for lines and text and the token colours (`var(--hl-k)`,
`var(--hl-nf)`, `var(--hl-m)`, `var(--hl-nb)`, `var(--hl-bp)`) for accents so it works in both colour
schemes; keep it small (`viewBox` around 400 wide, since the prose column is narrow).

## Links

- Paper: arXiv abstract URL (`https://arxiv.org/abs/<id>`), not the PDF.
- Other pages: relative (`gae.html`, `loss.html#s4`).
- Prior work the reader may need: link the paper, or its page here if implemented.
