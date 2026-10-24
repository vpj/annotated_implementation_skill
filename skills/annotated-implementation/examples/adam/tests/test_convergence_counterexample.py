"""Reddi et al. (2018), Theorem 1: an online convex problem on which Adam converges to the worst point."""
import pytest
import torch

from adam import Adam


def online_problem(optimizer_factory, c, n_steps=6000):
    x = torch.nn.Parameter(torch.tensor([0.0], dtype=torch.float64))
    optimizer = optimizer_factory([x])
    for t in range(1, n_steps + 1):
        optimizer.param_groups[0]['lr'] = 0.5 / t ** 0.5
        x.grad = torch.tensor([c if t % 3 == 1 else -1.0], dtype=torch.float64)
        optimizer.step()
        with torch.no_grad():
            x.clamp_(-1.0, 1.0)
    return x.item()


@pytest.mark.parametrize('c', [3.0, 10.0])
def test_adam_converges_to_the_worst_point(c):
    beta2 = 1 / (1 + c ** 2)
    x = online_problem(lambda p: Adam(p, betas=(0.0, beta2), eps=1e-12), c)
    assert x == pytest.approx(1.0)


@pytest.mark.parametrize('c', [3.0, 10.0])
def test_amsgrad_finds_the_optimum(c):
    beta2 = 1 / (1 + c ** 2)
    x = online_problem(lambda p: torch.optim.Adam(p, betas=(0.0, beta2), eps=1e-12, amsgrad=True), c)
    assert x < -0.9
