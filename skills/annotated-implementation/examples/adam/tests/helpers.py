import torch


def run(optimizer_cls, grads, **kwargs):
    param = torch.zeros(grads.shape[1:], dtype=torch.float64, requires_grad=True)
    optimizer = optimizer_cls([param], **kwargs)
    trajectory = []
    for g in grads:
        param.grad = g.clone()
        optimizer.step()
        trajectory.append(param.detach().clone())
    return torch.stack(trajectory)


def steps(optimizer_cls, grads, **kwargs):
    trajectory = run(optimizer_cls, grads, **kwargs)
    previous = torch.cat([torch.zeros_like(trajectory[:1]), trajectory[:-1]])
    return trajectory - previous


def train_regression(optimizer_cls, n_steps=300, **kwargs):
    torch.manual_seed(0)
    x = torch.randn(256, 8, dtype=torch.float64)
    y = x @ torch.randn(8, 1, dtype=torch.float64) + 0.01 * torch.randn(256, 1, dtype=torch.float64)
    model = torch.nn.Linear(8, 1).double()
    optimizer = optimizer_cls(model.parameters(), **kwargs)
    losses = []
    for _ in range(n_steps):
        optimizer.zero_grad()
        loss = torch.nn.functional.mse_loss(model(x), y)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
    return model, losses
