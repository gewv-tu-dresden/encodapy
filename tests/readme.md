# Tests

- Contains tests for the functionality of the framework.
- Tests are structured as follows:
  - [core](./core/): Tests for the core functions of EnCoDaPy
  - [components](./components/): Tests for the components in `encodapy.components`
- Tests are executed via GitHub Actions in [.github/workflows/tests.yml](./../.github/workflows/tests.yml)
- To run the tests locally, execute the following command in the root directory of the repository:

    ```bash
    poetry run pytest --cov=encodapy --cov-report=term-missing
    ```

## Test Distribution in `core/`

The `tests/core/` directory follows a responsibility-based organization:

| Directory        | Responsibility            | Test Focus                                    |
| ---------------- | ------------------------- | --------------------------------------------- |
| `basicservice/`  | Service orchestrator      | Service lifecycle, data flow, orchestration   |
| `communication/` | Interface implementations | FIWARE, MQTT, FILE communication handling     |
| `config/`        | Configuration management  | Config loading, validation, error handling    |
| `data/`          | Data processing           | Static data loading, data transformation      |
| `units/`         | Unit conversion           | Time unit conversion, component unit handling |

This structure ensures:

- **Single Responsibility**: Each test file focuses on one specific aspect
- **No Duplication**: Common fixtures are defined once in `basicservice/conftest.py` and re-exported via `core/conftest.py`
- **Clear Ownership**: Easy to locate tests for any given functionality
