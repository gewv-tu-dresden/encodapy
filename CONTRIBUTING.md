# Contributing to EnCoDaPy

Thanks for your interest in contributing to EnCoDaPy.

## Ways to contribute

You can help by:

- reporting bugs or suggesting improvements
- improving documentation and examples
- adding or refining tests
- contributing code changes

## Development setup

1. Install Poetry.
2. Create a local environment and install dependencies:

   ```bash
   poetry install
   ```

3. Run the test suite:

   ```bash
   poetry run pytest
   ```

## Contribution workflow

- Open an issue first for significant changes or bug fixes.
- Create a dedicated branch for your work.
- Keep changes focused and include tests where possible.
- Run the relevant checks before opening a pull request.
- GitHub Actions workflows for tests, linting, and documentation will run automatically for pushes and pull requests. Please make sure the relevant checks are green before asking for review.

## Pull requests

Please include:

- a short summary of the change
- the motivation for the change
- any relevant testing information

A clear and consistent PR title helps reviewers quickly understand the change. A simple convention is:

- `fix: ...` for bug fixes
- `feat: ...` for new features
- `docs: ...` for documentation changes
- `chore: ...` for maintenance or tooling updates

Examples:

- `fix: handle invalid input data in basic service`
- `feat: add support for additional output formats`
- `docs: clarify contribution workflow`

## Support and expectations

This project is maintained on a best-effort basis. Bug reports and feature requests are welcome, but response times may vary.
