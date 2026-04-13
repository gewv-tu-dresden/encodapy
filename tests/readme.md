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
