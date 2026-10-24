import math

import pytest
import torch

from adam import AdaMax
from helpers import run, steps, train_regression

BETA1, BETA2 = 0.9, 0.999


def algorithm_2(grads, alpha, beta1, beta2):
    """Algorithm 2 of the paper, line by line."""
    theta = torch.zeros(grads.shape[1:], dtype=torch.float64)
    m = torch.zeros_like(theta)
    u = torch.zeros_like(theta)
    trajectory = []
    for t, g in enumerate(grads, start=1):
        m = beta1 * m + (1 - beta1) * g
        u = torch.maximum(beta2 * u, g.abs())
        theta = theta - (alpha / (1 - beta1 ** t)) * m / u
        trajectory.append(theta.clone())
    return torch.stack(trajectory)


def test_equals_algorithm_2():
    torch.manual_seed(0)
    grads = torch.randn(200, 5, dtype=torch.float64)
    ours = run(AdaMax, grads, lr=0.01, betas=(BETA1, BETA2), eps=0.0)
    torch.testing.assert_close(ours, algorithm_2(grads, 0.01, BETA1, BETA2), rtol=1e-12, atol=1e-14)


def test_matches_torch_adamax():
    _, ours = train_regression(AdaMax, n_steps=50, lr=0.01)
    _, reference = train_regression(torch.optim.Adamax, n_steps=50, lr=0.01)
    assert ours == pytest.approx(reference, rel=1e-9)


@pytest.mark.parametrize('p', [50.0, 500.0, 5000.0])
def test_u_is_the_limit_of_the_lp_moving_average(p):
    torch.manual_seed(3)
    t = 300
    g = torch.randn(t, dtype=torch.float64).abs()

    u = torch.zeros((), dtype=torch.float64)
    for g_i in g:
        u = torch.maximum(BETA2 * u, g_i)

    i = torch.arange(1, t + 1, dtype=torch.float64)
    log_terms = p * (t - i) * math.log(BETA2) + p * g.log()
    log_v = math.log1p(-BETA2 ** p) + torch.logsumexp(log_terms, dim=0)
    lp_norm = torch.exp(log_v / p)

    assert lp_norm.item() == pytest.approx(u.item(), rel=10 / p)


def test_u_needs_no_bias_correction():
    grads = torch.tensor([[0.3], [0.2], [0.1]], dtype=torch.float64)
    first_step = steps(AdaMax, grads, lr=1.0, eps=0.0)[0]
    torch.testing.assert_close(first_step, torch.tensor([-1.0], dtype=torch.float64))


def test_typical_steps_are_bounded_by_alpha():
    torch.manual_seed(4)
    largest = steps(AdaMax, torch.randn(2000, 10, dtype=torch.float64), lr=1.0, eps=0.0).abs().max().item()
    assert largest <= 1.0 + 1e-12


def test_alpha_bound_is_exceeded_by_decreasing_gradients():
    t = 2000
    grads = torch.tensor([[BETA2 ** -(t - i)] for i in range(1, t + 1)], dtype=torch.float64)
    largest = steps(AdaMax, grads, lr=1.0, eps=0.0).abs().max().item()
    worst_case = (1 - BETA1) / (1 - BETA1 / BETA2)
    assert largest > 1.0
    assert largest == pytest.approx(worst_case, rel=1e-9)


def test_minimizes_regression_loss():
    _, losses = train_regression(AdaMax, lr=0.05)
    assert losses[-1] < 0.01 * losses[0]


def test_zero_gradients_do_not_produce_nan():
    grads = torch.zeros(10, 3, dtype=torch.float64)
    assert torch.isfinite(run(AdaMax, grads)).all()
