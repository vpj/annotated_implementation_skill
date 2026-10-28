import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import charts  # noqa: E402
from adam import Adam  # noqa: E402
from adam.convergence import OnlineProblem  # noqa: E402

N_STEPS = 6000
ALPHA = 0.5
CS = [3.0, 10.0]
EVERY = 10


def optimizers(c):
    beta2 = 1 / (1 + c ** 2)
    return {
        'adam': lambda p: Adam(p, betas=(0.0, beta2), eps=1e-12),
        'amsgrad': lambda p: torch.optim.Adam(p, betas=(0.0, beta2), eps=1e-12, amsgrad=True),
    }


def main():
    start = time.time()
    records = []
    for c in CS:
        for method, make_optimizer in optimizers(c).items():
            problem = OnlineProblem(c)
            regret = problem.average_regret(problem.run(make_optimizer, n_steps=N_STEPS, alpha=ALPHA))
            steps = list(range(EVERY, N_STEPS + 1, EVERY))
            regret = [float(f'{r:.4g}') for r in regret[EVERY - 1::EVERY]]
            records.append({'method': method, 'c': c, 'values': {'step': steps, 'average_regret': regret}})
    settings = {'n_steps': N_STEPS, 'alpha': ALPHA, 'cs': CS, 'beta1': 0.0, 'beta2': '1 / (1 + c^2)',
                'eps': 1e-12, 'every': EVERY}
    charts.write_records(ROOT / 'experiments' / 'results' / 'convergence.json', records, settings)
    print(f'{time.time() - start:.1f}s')


if __name__ == '__main__':
    main()
