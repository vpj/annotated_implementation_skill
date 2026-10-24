---
name: annotated-implementation
description: Implement a research paper (or take existing Python code) and publish it as an annotated, side-by-side HTML walkthrough - explanations, derivations and proofs with KaTeX math on the left, the tested code on the right. Use when the user asks to implement a paper with explanations, write an annotated/literate implementation, explain a codebase or algorithm line by line next to its math, or produce a paper-implementation tutorial page.
---

# Annotated Implementation

Produce a tested, plain Python implementation of a paper and a set of HTML pages that explain it
section by section: prose and math on the left, the exact code it describes on the right.

The code and the explanation are kept in separate files and joined at build time:

- `<module>.py` - plain, runnable Python. **No comments and no docstrings.** All explanation goes
  in the annotation.
- `tests/` - tests that prove the implementation is correct. Never rendered, never linked.
- `annotations/<page>.doc.html` - one per page. HTML `<section>` fragments; each one says which
  line of the code file it starts at (`data-start`) and what that line contains (`data-expect`).
- `scripts/build.py` (in this skill) - validates the annotations against the code and writes the
  pages. It also prints numbered listings to annotate against.
- `scripts/paper_text.py` (in this skill) - saves the paper's PDF and extracted text into the
  project.

In the commands below, `<skill>` is this skill's base directory.

Read `references/format.md` before writing the first annotation and `references/writing-guide.md`
before writing any prose.

`examples/adam/` is a complete project produced with this skill (Adam and AdaMax, PyTorch), built
with depth "derivations + proof sketch" and no experiment. Read the part that matches what you are
writing, not all of it:

| Writing | Look at |
|---|---|
| plain code | `adam/adam.py`, `adam/adamax.py` |
| tests, including tests of the paper's claims | `tests/test_adam.py`, `tests/test_adamax.py`; a published counterexample in `tests/test_convergence_counterexample.py`; `tests/conftest.py`, `tests/helpers.py` |
| an overview page | `annotations/index.doc.html` |
| a component page: section granularity, doc vs note sections, derivations above the code they justify, notes correcting the paper | `annotations/adam.doc.html` |
| a derivation by limits, and a correction backed by a test | `annotations/adamax.doc.html` |
| a prose-only theorem and proof page | `annotations/convergence.doc.html` |

Build it with `python <skill>/scripts/build.py <skill>/examples/adam/annotations/*.doc.html --out
<somewhere>` to see the rendered result.

## Workflow

Work through the phases in order. **The three checkpoints are hard stops**: present what is asked,
then end your turn and wait for the user's answer. Silence is not approval.

### Phase 1 - Read and scope

1. Read everything given: the paper, existing code, and the user's instructions. Save the paper
   into the project first, then read the text file:
   `python <skill>/scripts/paper_text.py <arXiv id | URL | file.pdf> --out <topic>/paper`
   This writes `paper.pdf` and `paper.txt` with page markers. Use this, not a web fetch of the
   PDF; fetch tools return compressed PDF bytes, and later phases (checkpoint B especially) need
   to quote the paper's equations and proofs again. If `pypdf` is missing, install it.
2. List the paper's components (models, losses, algorithms, training procedure) and the **prior
   papers it depends on** (e.g. PPO depends on GAE for advantages).
3. Draft a **page plan**: an overview page, a page per component worth its own explanation, a page
   per dependency that will be implemented, and an optional experiment page. One line per page
   saying what it covers and which code file it annotates.

If the user handed you existing code instead of a paper, the plan maps their files to pages, and
Phase 3 becomes "strip comments/docstrings into notes, add tests, run them".

### Phase 2 - Scoping interview

Ask with `AskUserQuestion` (multiple choice, your recommendation first and marked). Ask only what
the request has not already answered. `AskUserQuestion` takes at most four questions per call: ask
the first four, then the rest in a second call, or state your default for the last one in the plan
you present for approval. Cover:

1. **Implementation scope** - core method only, or the full method with the paper's variants and
   ablations.
2. **Dependencies** - for each prior paper the method needs: implement it as its own annotated page,
   or use an existing library implementation and link to it.
3. **Documentation depth**
   - intuition and the key equations;
   - full derivations of the main results;
   - derivations plus proofs (for each proof: reproduce in full, give a sketch, or link to it).
4. **Experiment**
   - none;
   - minimal toy experiment (synthetic data, CPU, runs in minutes);
   - real training script.
   For the last two, follow up on dataset/environment, compute budget, and which metric to report.
5. **Framework and audience** - framework (default PyTorch) and what the reader is assumed to
   know, which decides what gets explained and what is taken as given.

Then show the page plan, updated with the answers, and the project layout you will use (default
below; adapt to an existing project). **Wait for approval.**

```
<topic>/
├── paper/                # paper.pdf, paper.txt (from paper_text.py)
├── <package>/            # plain Python, one module per code page
├── tests/                # pytest; correctness only, never rendered
│   └── conftest.py       # puts the project root and tests/ on sys.path
├── annotations/          # <page>.doc.html
└── site/                 # generated by build.py
```

### Phase 3 - Implement and test

1. Write the modules: clear names, type hints, no comments, no docstrings. Follow the paper's
   notation in variable names where it stays readable (`log_pi`, `advantage`, `clip_eps`).
2. Write tests in `tests/` that show the code is **correct**, not merely that it runs:
   - a naive or explicit version of the paper's formula against the optimized implementation
     (e.g. a recursive advantage estimator against the explicit discounted sum);
   - known values, limits and edge cases from the paper (e.g. a ratio of 1 is never clipped);
   - shapes, dtypes, and invariants (normalization, probabilities sum to 1, masking);
   - gradients where they matter (`torch.autograd.gradcheck`, or a finite-difference check);
   - a tiny overfit or loss-decreases check for anything trainable;
   - for an experiment, a smoke test that runs a few steps end to end.
3. Test the **paper's claims**, not only the code: every bound, limit, invariance, or "this is
   always at most X" the pages will repeat. Try to break each one, e.g. with an adversarial input
   built from the equality case of the inequality the paper relies on. Papers are sometimes wrong,
   and a claim the page states must be one you have checked. If a claim fails, keep the test (it
   asserts what actually happens) and report it at checkpoint A.
4. Put shared test helpers in `tests/helpers.py` and add `tests/conftest.py` that inserts the
   project root and `tests/` into `sys.path`, so `pytest tests` works from the project root.
5. Run the tests until they all pass. Fix the implementation, not the test, unless the test is
   wrong - and say so if it was.

**Checkpoint A - implementation review.** Present:
- the files and the main classes and functions;
- a paper-to-code map: each key equation (with the paper's equation number) next to the
  `file:line` that implements it;
- the test results and what each test checks;
- every **deviation from the paper**: numerical-stability tricks, simplifications, assumed
  hyperparameters the paper does not state;
- every **paper claim the tests found to be wrong or loose**, with the measured value.

Stop and wait for approval or changes.

### Phase 4 - Annotate

1. Freeze the code. Print numbered listings to annotate against:
   `python <skill>/scripts/build.py --listing <package>/<module>.py`
2. **Checkpoint B - derivations and proofs** (only if the depth answer includes derivations or
   proofs). For each one, present:
   - the paper's original derivation or proof, summarized step by step with its equation numbers;
   - how you will present it: steps expanded, steps skipped or linked, notation changed to match
     the code;
   - which code section it will sit above.

   Stop and wait for approval.
3. Write the overview page and the core page first, build them, and show the user where they are.
   **Checkpoint C** - ask whether the tone, depth and section granularity are right before writing
   the remaining pages. Stop and wait.
4. Write the remaining pages following `references/writing-guide.md`.
5. Compute every number the prose states (ratios, bounds, constants at the default
   hyperparameters) with a quick Python calculation instead of estimating it. Checkpoints only
   catch a wrong number if the user happens to recompute it.

If the code must change after annotating, rerun the tests, rerun `--listing`, and let the build's
`data-expect` errors tell you which sections moved.

### Phase 5 - Build and check

1. Build: `python <skill>/scripts/build.py annotations/*.doc.html --out site`
   Build all pages together and fix every error and every warning: broken relative links (the
   build checks them against the other pages), and comments or docstrings left in the code.
2. Serve the site (`python -m http.server --directory site`) and open every page in a browser if
   one is available (or ask the user to), with the window at least 900px wide: the overflow check
   measures the layout at the current width. Each page publishes a self-check once it has rendered:
   evaluate `window.annotationReport` with a JavaScript tool, or look for the red banner. It lists
   math errors, display equations wider than their column, and text that still contains `$`
   (math that was not rendered). Fix all of them; split wide equations over lines of an `align*`.
   At a desktop width (at least 900px) also look at each page: diagrams render, sections line up
   with their code, and clicking a key symbol in an equation lights up its other occurrences.
3. Report: the pages produced (paths), test results, deviations from the paper, and anything
   left out of scope.

## Rules

- Code files stay plain. If something needs explaining, it goes in the annotation.
- Tests never appear in the pages and pages never link to them.
- Never skip a checkpoint because the change seems small or the user seems busy.
- Write every symbol with identical LaTeX everywhere on a page (`\hat{A}_t`, never sometimes
  `\hat A_t`); clicking a symbol highlights every equal expression, and that only works on exact
  matches.
- The reader does not have the paper. Never refer to "Eq. 3", "Fig. 14", "Algorithm 1" or
  "Section 3.1" instead of saying what it is: restate the equation or idea, or link to where this
  site shows it (give that equation or figure an `id`). The paper's own label may appear only in
  `<span class="paper-ref">` beside the restated content; the build warns about any other.
  Checkpoint messages to the user may still use the paper's numbering.
- Pages are self-contained HTML plus the `assets/` folder the build copies next to them. Code is
  highlighted at build time; only KaTeX loads from a public CDN.
