import pytest
import torch
from packaging import version
from problems import get_problem
from pytest import approx

from torchode import AutoDiffAdjoint, Dopri5, Euler, Heun, IntegralController, Tsit5

torch_version = version.parse(torch.__version__)


@pytest.mark.parametrize("step_method", [Dopri5, Heun, Tsit5, Euler])
def test_can_be_jitted_with_torch_script(step_method):
    _, term, problem = get_problem("sine", [[0.1, 0.15, 1.0], [1.0, 1.9, 2.0]])
    step_size_controller = IntegralController(1e-3, 1e-3, term=term)
    adjoint = AutoDiffAdjoint(step_method(term), step_size_controller)
    jitted = torch.compile(adjoint)

    dt0 = torch.tensor([0.01, 0.01]) if step_method is Euler else None
    solution = adjoint.forward(problem, dt0=dt0)
    solution_jit = jitted.solve(problem, dt0=dt0)

    assert solution.ts == approx(solution_jit.ts)
    assert solution.ys == approx(solution_jit.ys, abs=1e-3, rel=1e-3)


methods = [Dopri5, Heun, Tsit5]
v = torch_version
if (v.major, v.minor) not in [(2, 0)]:
    # In pytorch 2.0, Euler triggers an internal error in the JIT compiler specifically
    # in this next test, so we just exclude it
    methods.append(Euler)


@pytest.mark.parametrize("step_method", methods)
def test_passing_term_dynamically_equals_fixed_term(step_method):
    _, term, problem = get_problem("sine", [[0.1, 0.15, 1.0], [1.0, 1.9, 2.0]])

    dt0 = torch.tensor([0.01, 0.01]) if step_method is Euler else None

    controller = IntegralController(1e-3, 1e-3)
    adjoint = AutoDiffAdjoint(step_method(None), controller)
    solution = adjoint.forward(problem, term, dt0=dt0)

    controller_jit = IntegralController(1e-3, 1e-3, term=term)
    adjoint_jit = AutoDiffAdjoint(step_method(term), controller_jit)
    solution_jit = torch.compile(adjoint_jit).solve(problem, dt0=dt0)

    assert solution.ts == approx(solution_jit.ts)
    assert solution.ys == approx(solution_jit.ys, abs=1e-3, rel=1e-3)
