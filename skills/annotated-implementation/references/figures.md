# Figures and charts

The writing guide ("Diagrams") says when to draw and what a figure must show. This file says how to
build figures that show data: charts of experiment results, plots of what the code computes, and
result tables. The examples use the Adam project in `examples/adam/`.

## Pipeline

Three steps, each in its own file. Keep them apart so that restyling a chart never re-runs training.

1. **Experiment**: the training and evaluation code is a file of the package
   (`<package>/experiment.py`), annotated like the rest; it returns its results and saves nothing.
   A thin runner outside the package, `experiments/run_<name>.py`, calls it for each seed and
   setting and saves every run with `charts.write_records` to `experiments/results/<name>.json`. Do
   no plotting and no averaging in either. Print how long it takes; keep it to a few minutes on a
   CPU.
2. **Figures** (`scripts/figures.py`, outside the package): read the records with
   `charts.load_records` and build each figure with the helpers in `charts.py`. A figure that shows
   what the code computes for one input (a learning-rate schedule, a distribution, a mask) calls the
   implementation directly, with a fixed seed and `float64`. Never train in this script.
3. **Placement**: each figure is a function that returns a string.
   `charts.replace_markers(annotations, FIGURES)` rewrites the text between `<!-- figure:name -->` and `<!-- /figure:name -->` in each
   annotation file. It stops with an error if a marker has no function or a function has no marker.
   The generated SVG is committed inside the annotation; the site build does not run the script.

After changing an experiment: run it, run `figures.py`, build, then check the HTML.

## The helpers: `scripts/charts.py`

Copy `<skill>/scripts/charts.py` into the project's `scripts/` folder (the project then has no
dependency on the skill) and import it from `figures.py`. It uses the standard library only. Do not
write your own `svg`, `panel` or `legend`: the shared file is what keeps the margins, fonts, ticks
and checks the same in every chart. If a chart needs something the helpers do not do, add it to
`charts.py` in the skill, not to one project.

It has:

- `write_records`, `load_records`: the record file (below).
- `select(records, **fields)`, `mean_curve(records, field, **fields)`, `spread(...)`: the records
  whose fields equal the given values exactly, and the mean or the min and max over them (usually
  over the seeds).
- `Line(values, color, dashed=False, band=None)`: one line of a panel.
- `panel(x0, width, height, lines, steps, title, *, x_label, y_label, y_range, log=False,
  every=1)`: one set of axes. The labels and the y range are required.
- `legend(items, y, x0, spacing)`: one row of `(label, Line)` samples.
- `svg(width, height, label, body)`: the `<svg>` element.
- `replace_markers(annotations, figures)`.

`panel` and `legend` raise an error for a y label longer than the plot, a title wider than the
panel, more than five colours, two lines with the same colour and dash, fewer than two steps, a line with the wrong number of values, a value
outside `y_range` (it would be drawn flat along the edge), a log axis that starts at 0 or has no
power of 10 to label, and a legend label wider than its spacing or past the right edge. Labels are
escaped, so `<` and `&` are safe in titles and legends.

## Records

Store each run as one record with named fields and a `values` dict of curves:

```json
{"settings": {"steps": 400, "seeds": 3, "lr": 0.001},
 "records": [
   {"method": "adam", "seed": 0, "values": {"step": [0, 4, 8], "loss": [2.31, 1.87, 1.52]}},
   {"method": "adamax", "seed": 0, "values": {"step": [0, 4, 8], "loss": [2.31, 1.95, 1.64]}}
 ]}
```

Select by field (`mean_curve(records, 'loss', method='adam')`), never by building or splitting a
string key such as `"adam|seed0"`: prefix matching on keys also matches `"adam + amsgrad"`.
`select` compares each field exactly and raises an error if nothing matches.

## Commit the results

Commit `experiments/results/<name>.json` so that someone with a fresh clone can restyle or fix a
figure without running the experiment again. Keep it small (under about 1 MB):

- record only the curves that a figure or table uses;
- record every 4th or 10th step, not every step;
- round to 4 significant digits.

If the results cannot be made that small, put them in a gitignored folder (`experiments/runs/`) and
say so in the experiment's annotation: "the figures need `run_<name>.py` (about N minutes) before
`figures.py` can run". That is a trade-off; choose it on purpose, not by default.

## No plotting library

Do not use matplotlib, plotly or images. A library's SVG hard-codes colours and fonts, so it fails
in dark mode and does not match the rest of the HTML; it draws math as paths, so the labels are not typeset by
KaTeX and do not link to the prose; and it is large. The SVG from `charts.py` uses `currentColor`
and the theme tokens, takes `$...$` labels, and stays a few kilobytes.

## Layout (viewBox units)

`charts.py` fixes the margins and font sizes. You choose:

- Width 400 (the prose column): one panel of 400, or two panels of 200 side by side at `x0 = 0`
  and `x0 = 200`. Panel height about 170.
- The legend rows: under the panels, at `y = height + 16`, then 18 lower for each further row. Add
  their height to the `svg` height. Never put a legend over the plot area.
- A y label short enough for the plot height. If it is not, use the symbol
  (`$\lVert \theta - \theta_0 \rVert$`) and define it in the caption.

## Axes and ticks

`charts.py` draws the left and bottom axes, three ticks on a linear y axis, one tick per decade on
a log y axis, and x ticks at the first step, the middle (rounded to two significant digits, so
3005 is labelled 3000) and the last step. Pass the recorded steps as `steps`, so
that the tick labels are step counts, not array indices.

Choose `y_range` from what the quantity means, not from the data: an accuracy is always 0 to 1.
Give panels that the reader compares the same `y_range`.

## Lines

- Colour is the method; dashes are a variant of it (for example, dashed = with weight decay). Give
  the dash meaning its own legend row, drawn with `Line(..., 'currentColor', dashed=True)`.
- Give each method a fixed colour from `charts.COLORS` at the top of `figures.py`
  (`ADAM = COLORS[0]`). A method has the same colour and dash in every figure of the project.
- For long curves pass `every=4` to draw every 4th point; the last point is always drawn.
- At most five colours in a panel, each at most twice (solid and dashed). Use more panels if there
  are more.
- Plot the mean over seeds and give the number of seeds in the caption. If the spread between
  seeds matters to the claim, pass `band=spread(records, 'loss', method='adam')`.

## Tables

Generate result tables from the same records, in `figures.py`, with the same markers. Use a fixed
number of decimals. Each column header names the quantity and the setting
("final loss, $\beta_2 = 0.999$"); put the step in a second header row.

## Check

After `figures.py`, build and open the HTML at desktop width, in both colour schemes and in WebKit
(see the self-check in `SKILL.md`). Look for a legend on top of a line, a label outside the `svg`,
and a panel title that runs into the next panel. Then cover the prose and read the chart from the
figure and its caption only (writing guide, "Charts and tables must be readable without the
prose").
