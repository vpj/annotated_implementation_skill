from pathlib import Path

import charts

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / 'experiments' / 'results'

ADAM = charts.COLORS[0]
AMSGRAD = charts.COLORS[1]


def counterexample() -> str:
    records = charts.load_records(RESULTS / 'convergence.json')
    body = ''
    for x0, c, y_max in [(0, 3.0, 1), (200, 10.0, 8)]:
        steps = charts.mean_curve(records, 'step', method='adam', c=c)
        adam = charts.Line(charts.mean_curve(records, 'average_regret', method='adam', c=c), ADAM)
        amsgrad = charts.Line(charts.mean_curve(records, 'average_regret', method='amsgrad', c=c), AMSGRAD)
        limit = charts.Line([2 * (c - 2) / 3] * len(steps), 'currentColor', dashed=True)
        body += charts.panel(x0, 200, 170, [limit, adam, amsgrad], steps, f'$C = {c:g}$',
                             x_label='step $T$', y_label='$R(T) / T$', y_range=(0, y_max), every=4)
    body += charts.legend([('Adam', charts.Line([], ADAM)),
                           ('AMSGrad', charts.Line([], AMSGRAD)),
                           ('$2 (C - 2) / 3$', limit)], y=186, spacing=90)
    return charts.svg(400, 196, 'Average regret of Adam and AMSGrad on the counterexample, for C = 3 and C = 10', body)


FIGURES = {
    'counterexample': counterexample,
}


def main():
    charts.replace_markers(sorted((ROOT / 'adam').glob('*.doc.html')), FIGURES)


if __name__ == '__main__':
    main()
