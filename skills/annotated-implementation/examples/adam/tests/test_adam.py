import math

import pytest
import torch

from adam import Adam
from helpers import run, steps, train_regression

BETA1, BETA2 = 0.9, 0.999


def algorithm_1(grads, alpha, beta1, beta2, eps):
    """Algorithm 1 of the paper, line by line."""
    theta = torch.zeros(grads.shape[1:], dtype=torch.float64)
    m = torch.zeros_like(theta)
    v = torch.zeros_like(theta)
    trajectory = []
    for t, g in enumerate(grads, start=1):
        m = beta1 * m + (1 - beta1) * g
        v = beta2 * v + (1 - beta2) * g * g
        m_hat = m / (1 - beta1 ** t)
        v_hat = v / (1 - beta2 ** t)
        theta = theta - alpha * m_hat / (v_hat.sqrt() + eps)
        trajectory.append(theta.clone())
    return torch.stack(trajectory)


@pytest.mark.parametrize('eps', [0.0, 1e-8, 1e-3])
def test_efficient_ordering_equals_algorithm_1(eps):
    torch.manual_seed(0)
    grads = 1e-3 * torch.randn(200, 5, dtype=torch.float64)
    ours = run(Adam, grads, lr=0.01, betas=(BETA1, BETA2), eps=eps)
    reference = algorithm_1(grads, 0.01, BETA1, BETA2, eps)
    torch.testing.assert_close(ours, reference, rtol=1e-10, atol=1e-14)


def test_matches_torch_adam():
    _, ours = train_regression(Adam, n_steps=50, lr=0.01)
    _, reference = train_regression(torch.optim.Adam, n_steps=50, lr=0.01)
    assert ours == pytest.approx(reference, rel=1e-9)


def test_first_step_has_magnitude_alpha():
    grads = torch.tensor([[3.0, -0.002, 50.0]], dtype=torch.float64)
    step = steps(Adam, grads, lr=0.1, eps=0.0)[0]
    torch.testing.assert_close(step, -0.1 * grads[0].sign())


def test_invariant_to_gradient_scale():
    torch.manual_seed(1)
    grads = torch.randn(100, 4, dtype=torch.float64)
    torch.testing.assert_close(run(Adam, grads, eps=0.0), run(Adam, 1e4 * grads, eps=0.0))


def test_sparse_gradient_step_matches_section_2_1():
    t = 2000
    grads = torch.zeros(t, 1, dtype=torch.float64)
    grads[-1] = 1.0
    step = steps(Adam, grads, lr=1.0, eps=1e-30)[-1].abs().item()
    expected = (1 - BETA1) / math.sqrt(1 - BETA2) * math.sqrt(1 - BETA2 ** t) / (1 - BETA1 ** t)
    assert step == pytest.approx(expected, rel=1e-12)
    assert step < (1 - BETA1) / math.sqrt(1 - BETA2)


def test_section_2_1_bound_is_exceeded_by_adversarial_gradients():
    t = 2000
    grads = torch.tensor([[(BETA1 / BETA2) ** (t - i)] for i in range(1, t + 1)], dtype=torch.float64)
    largest = steps(Adam, grads, lr=1.0, eps=0.0).abs().max().item()
    gamma = BETA1 ** 2 / BETA2
    cauchy_schwarz_bound = (1 - BETA1) / math.sqrt(1 - BETA2) / math.sqrt(1 - gamma)
    assert largest > (1 - BETA1) / math.sqrt(1 - BETA2)
    assert largest <= cauchy_schwarz_bound


def test_typical_steps_are_about_alpha():
    torch.manual_seed(2)
    largest = steps(Adam, torch.randn(2000, 10, dtype=torch.float64), lr=1.0, eps=0.0).abs().max().item()
    assert 0.5 < largest < 1.1


def test_minimizes_regression_loss():
    _, losses = train_regression(Adam, lr=0.05)
    assert losses[-1] < 0.01 * losses[0]


def test_closure_returns_loss():
    param = torch.nn.Parameter(torch.tensor([2.0]))
    optimizer = Adam([param])

    def closure():
        optimizer.zero_grad()
        loss = (param ** 2).sum()
        loss.backward()
        return loss

    assert optimizer.step(closure).item() == pytest.approx(4.0)


@pytest.mark.parametrize('kwargs', [dict(lr=0.0), dict(betas=(1.0, 0.999)), dict(betas=(0.9, -0.1)), dict(eps=-1.0)])
def test_rejects_invalid_hyperparameters(kwargs):
    with pytest.raises(ValueError):
        Adam([torch.nn.Parameter(torch.zeros(1))], **kwargs)
