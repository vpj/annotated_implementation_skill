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
    x = OnlineProblem(c).run(lambda p: Adam(p, betas=(0.0, beta2), eps=1e-12))[-1]
    assert x == pytest.approx(1.0)


@pytest.mark.parametrize('c', [3.0, 10.0])
def test_amsgrad_finds_the_optimum(c):
    beta2 = 1 / (1 + c ** 2)
    x = OnlineProblem(c).run(lambda p: torch.optim.Adam(p, betas=(0.0, beta2), eps=1e-12, amsgrad=True))[-1]
    assert x < -0.9


def test_run_returns_one_value_per_step():
    trajectory = OnlineProblem(3.0).run(lambda p: Adam(p, betas=(0.0, 0.1)), n_steps=7)
    assert len(trajectory) == 7
    assert all(-1.0 <= x <= 1.0 for x in trajectory)


@pytest.mark.parametrize('c', [3.0, 10.0])
def test_average_regret_matches_the_direct_sum(c):
    problem = OnlineProblem(c)
    trajectory = problem.run(lambda p: Adam(p, betas=(0.0, 1 / (1 + c ** 2)), eps=1e-12), n_steps=300)
    iterates = [0.0] + trajectory[:-1]

    def f(t, x):
        return c * x if t % 3 == 1 else -x

    direct = sum(f(t, x) - f(t, -1.0) for t, x in enumerate(iterates, 1)) / len(iterates)
    assert problem.average_regret(trajectory)[-1] == pytest.approx(direct)


@pytest.mark.parametrize('c', [3.0, 10.0])
def test_average_regret_at_a_fixed_point(c):
    problem = OnlineProblem(c)
    start = c / 300
    assert problem.average_regret([-1.0] * 300)[-1] == pytest.approx(start)
    assert problem.average_regret([1.0] * 300)[-1] == pytest.approx(2 * (c - 2) / 3 - start)


@pytest.mark.parametrize('c', [3.0, 10.0])
def test_adam_regret_does_not_vanish_but_amsgrad_regret_does(c):
    beta2 = 1 / (1 + c ** 2)
    problem = OnlineProblem(c)
    adam = problem.average_regret(problem.run(lambda p: Adam(p, betas=(0.0, beta2), eps=1e-12)))
    amsgrad = problem.average_regret(
        problem.run(lambda p: torch.optim.Adam(p, betas=(0.0, beta2), eps=1e-12, amsgrad=True))
    )
    assert adam[-1] == pytest.approx(2 * (c - 2) / 3, rel=0.05)
    assert abs(amsgrad[-1]) < 0.05 * c
