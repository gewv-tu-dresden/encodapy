# FlixoptModelComponent Tests

This folder contains the tests for the FlixoptModelComponent.
The goal is to cover data preparation, model assembly, optimization runtime,
and output mapping in a maintainable way.

## Structure

- [test_flixopt_model_component_helpers.py](./unit/test_flixopt_model_component_helpers.py): helper methods, input handling,
  logging forwarding, and simple control-flow checks.
- [test_flixopt_model_component.py](./unit/test_flixopt_model_component.py): regression test ensuring that a failed
  optimization clears stale output data from the previous run.
- [test_flixopt_model_component_runtime.py](./unit/test_flixopt_model_component_runtime.py): runtime behavior, converter
  dispatch, and optimization success and failure paths.
- [test_flixopt_model_component_branches.py](./unit/test_flixopt_model_component_branches.py): targeted branch and edge-case
  tests for defensive and hard-to-reach code paths.
- [test_flixopt_model_component_output_mapping.py](./integration/test_flixopt_model_component_output_mapping.py):
  integration-style checks for result export and domain output mapping.
- [test_flixopt_model_component_bidirectional_output.py](./integration/test_flixopt_model_component_bidirectional_output.py):
  focused integration check for bidirectional forward-minus-reverse output mapping.
- [test_flixopt_model_component_solver_execution.py](./integration/test_flixopt_model_component_solver_execution.py):
  component-level end-to-end optimization test with a real Highs solver.
- [test_flixopt_example_config_smoke.py](./integration/test_flixopt_example_config_smoke.py):
  smoke test that runs the real example configuration from examples/09_flixopt.

## Prerequisites

- Unit tests run without an external solver.
- Integration tests with real optimization require the optional dependency highspy.
- If highspy is not installed, solver-based integration tests are skipped.
- Solver runs can create results/encodapy.log as a side effect.

## Running the tests

Run only this component suite:

```bash
poetry run pytest tests/components/flixopt_model_component -q
```

Run only integration tests in this component suite:

```bash
poetry run pytest tests/components/flixopt_model_component -m integration -q
```

Run only the example-based smoke test:

```bash
poetry run pytest tests/components/flixopt_model_component/integration/test_flixopt_example_config_smoke.py -q
```

Run only the bidirectional output mapping integration test:

```bash
poetry run pytest tests/components/flixopt_model_component/integration/test_flixopt_model_component_bidirectional_output.py -q
```

Run the component suite with coverage for the target module:

```bash
poetry run pytest tests/components/flixopt_model_component --cov=encodapy.components.flixopt_model_component.flixopt_model_component --cov-report=term-missing -q
```

## Test files and scope

- [test_flixopt_model_component_helpers.py](./unit/test_flixopt_model_component_helpers.py): helper loading, input handling, data preparation, and logging-related behavior.
- [test_flixopt_model_component.py](./unit/test_flixopt_model_component.py): regression test for stale output data clearing on failed optimization.
- [test_flixopt_model_component_runtime.py](./unit/test_flixopt_model_component_runtime.py): runtime flow, converter dispatch, and optimization success/failure handling.
- [test_flixopt_model_component_branches.py](./unit/test_flixopt_model_component_branches.py): defensive branches and edge cases that are hard to reach in standard runtime tests.
- [test_flixopt_model_component_output_mapping.py](./integration/test_flixopt_model_component_output_mapping.py): integration-style checks for result export and output mapping.
- [test_flixopt_model_component_bidirectional_output.py](./integration/test_flixopt_model_component_bidirectional_output.py): focused check for net bidirectional mapping (forward minus reverse).
- [test_flixopt_model_component_solver_execution.py](./integration/test_flixopt_model_component_solver_execution.py): component-level solver execution with Highs and robust result invariants.
- [test_flixopt_example_config_smoke.py](./integration/test_flixopt_example_config_smoke.py): smoke execution of the real example configuration from examples/09_flixopt.

## Where test details live

- Detailed behavior of individual tests is documented in each test file through descriptive test names and function docstrings.
- Keep this README focused on scope, structure, and execution.

## Maintenance Notes

- Add new tests to the appropriate file group: helpers, runtime, branches, or integration.
- Keep test names in the form test_<behavior>_<expectation>.
- Update the file/scope list when new test files are added or responsibilities change.
- Keep solver-based tests robust by checking invariants instead of exact MIP values.
- Keep example smoke tests optional in CI or gated by integration marker.
