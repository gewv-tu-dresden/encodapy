# Tests

- Contains tests for the functionality of the framework.
- Tests are structured as follows:
  - [core](./core/): Tests for the core functions of EnCoDaPy
  - [components](./components/): Tests for the components in `encodapy.components`
- Tests are executed via GitHub Actions in [.github/workflows/tests.yml](./../.github/workflows/tests.yml)
- Tests use pytest markers to separate fast unit tests from slower integration and Docker tests:
  - `integration`: tests with optional external runtime dependencies (e.g. the Highs solver)
  - `docker`: tests requiring Docker containers started via `testcontainers`
  - `slow`: tests that take a long time to run
- To run the tests locally, execute the following command in the root directory of the repository:

    ```bash
    poetry run pytest --cov=encodapy --cov-report=term-missing
    ```

## Running with and without integration tests

By default the command above runs everything. Use the markers to select a subset:

```bash
# Unit tests only (skip integration and Docker tests) — no Docker required
poetry run pytest -m "not integration and not docker" --cov=encodapy --cov-report=term-missing

# Integration tests only (incl. Docker-based tests)
poetry run pytest -m "integration or docker" -v --cov=encodapy --cov-report=term-missing
```

### Docker-based integration tests

The Docker tests live in [docker/](./docker/) and start a full FIWARE stack
(Orion Context Broker, MongoDB, CrateDB, Mosquitto MQTT broker) via
`testcontainers` and `docker-compose.fiware.yml`.

Requirements:

- A running Docker daemon
- The `dev` dependency group installed (`poetry install --with dev`)

Run them with:

```bash
poetry run pytest tests/docker -m "docker" -v
```

Without Docker, exclude them with `-m "not docker"` (or `-m "not integration and not docker"`).

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
