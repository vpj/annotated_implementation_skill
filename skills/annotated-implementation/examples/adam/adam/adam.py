import math
from typing import Callable, Iterable, Optional, Tuple

import torch
from torch.optim import Optimizer


class Adam(Optimizer):
    def __init__(self, params: Iterable, lr: float = 1e-3, betas: Tuple[float, float] = (0.9, 0.999),
                 eps: float = 1e-8):
        if lr <= 0.0:
            raise ValueError(f'Invalid learning rate: {lr}')
        if not all(0.0 <= beta < 1.0 for beta in betas):
            raise ValueError(f'Invalid betas: {betas}')
        if eps < 0.0:
            raise ValueError(f'Invalid epsilon: {eps}')
        super().__init__(params, dict(lr=lr, betas=betas, eps=eps))

    @torch.no_grad()
    def step(self, closure: Optional[Callable[[], torch.Tensor]] = None) -> Optional[torch.Tensor]:
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            for param in group['params']:
                if param.grad is not None:
                    self.update(param, group)

        return loss

    def update(self, param: torch.Tensor, group: dict):
        grad = param.grad
        if grad.is_sparse:
            raise RuntimeError('Adam does not support sparse gradients')

        state = self.state[param]
        if not state:
            state['t'] = 0
            state['m'] = torch.zeros_like(param)
            state['v'] = torch.zeros_like(param)

        beta1, beta2 = group['betas']
        state['t'] += 1
        t, m, v = state['t'], state['m'], state['v']

        m.mul_(beta1).add_(grad, alpha=1 - beta1)
        v.mul_(beta2).addcmul_(grad, grad, value=1 - beta2)

        bias_correction1 = 1 - beta1 ** t
        bias_correction2 = 1 - beta2 ** t
        alpha_t = group['lr'] * math.sqrt(bias_correction2) / bias_correction1
        eps_hat = group['eps'] * math.sqrt(bias_correction2)

        param.addcdiv_(m, v.sqrt().add_(eps_hat), value=-alpha_t)
