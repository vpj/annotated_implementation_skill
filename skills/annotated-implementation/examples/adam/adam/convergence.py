from typing import Callable, List

import torch


class OnlineProblem:
    def __init__(self, c: float):
        self.c = c

    def gradient(self, t: int) -> torch.Tensor:
        if t % 3 == 1:
            return torch.tensor([self.c], dtype=torch.float64)
        return torch.tensor([-1.0], dtype=torch.float64)

    def run(
        self,
        make_optimizer: Callable[[List[torch.nn.Parameter]], torch.optim.Optimizer],
        n_steps: int = 6000,
        alpha: float = 0.5,
    ) -> List[float]:
        x = torch.nn.Parameter(torch.zeros(1, dtype=torch.float64))
        optimizer = make_optimizer([x])
        trajectory = []
        for t in range(1, n_steps + 1):
            optimizer.param_groups[0]['lr'] = alpha / t ** 0.5
            x.grad = self.gradient(t)
            optimizer.step()
            with torch.no_grad():
                x.clamp_(-1.0, 1.0)
            trajectory.append(x.item())
        return trajectory

    def average_regret(self, trajectory: List[float]) -> List[float]:
        regret = 0.0
        averages = []
        x = 0.0
        for t, x_next in enumerate(trajectory, 1):
            regret += self.gradient(t).item() * (x + 1.0)
            averages.append(regret / t)
            x = x_next
        return averages
