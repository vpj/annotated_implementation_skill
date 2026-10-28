"""Reddi et al. (2018), Theorem 1: an online convex problem on which Adam converges to the worst point."""
import pytest
import torch

from adam import Adam
from adam.convergence import OnlineProblem


@pytest.mark.parametrize('c', [3.0, 10.0])
def test_gradient_follows_the_three_step_cycle(c):
    problem = OnlineProblem(c)
    assert [problem.gradient(t).item() for t in range(1, 7)] == [c, -1.0, -1.0, c, -1.0, -1.0]


@pytest.mark.parametrize('c', [3.0, 10.0])
def test_adam_converges_to_the_worst_point(c):
    beta2 = 1 / (1 + c ** 2)
    x = OnlineProblem(c).run(lambda p: Adam(p, betas=(0.0, beta2), eps=1e-12))
    assert x == pytest.approx(1.0)


@pytest.mark.parametrize('c', [3.0, 10.0])
def test_amsgrad_finds_the_optimum(c):
    beta2 = 1 / (1 + c ** 2)
    x = OnlineProblem(c).run(lambda p: torch.optim.Adam(p, betas=(0.0, beta2), eps=1e-12, amsgrad=True))
    assert x < -0.9
