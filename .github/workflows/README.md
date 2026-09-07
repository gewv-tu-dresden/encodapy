# GitHub Actions – Workflow Overview

This directory contains all CI/CD workflows for the `encodapy` project
(*Energy Control and Data Preparation in Python*).
GitHub automatically runs every YAML file located in `.github/workflows`.

The project uses a **Conventional Commits** based workflow: PR titles are
validated, `release-please` maintains a release PR and creates version tags,
and pushing a `v*` tag triggers the full publish pipeline.

## Overview

| Workflow file          | Name                           | Purpose                                                   | Trigger                                      |
|------------------------|--------------------------------|-----------------------------------------------------------|----------------------------------------------|
| `lint-pr-title.yml`    | lint-pr-title                  | Validate that PR titles follow Conventional Commits       | `pull_request` (opened, edited, synchronize, reopened) |
| `tests.yml`            | Tests                          | Run pytest (with coverage) + test-build the docs          | `push` (main), `pull_request`                |
| `pylint.yml`           | Pylint                         | Static code analysis with Pylint                          | `push` (main), `pull_request`                |
| `release-please.yml`   | release-please                 | Maintain release PR & create version tags/changelog       | `push` (main)                                |
| `docs.yml`             | Build and Deploy Documentation | Build docs & deploy `main` version to GitHub Pages        | `push` (main)                                |
| `release.yml`          | Publish Release                | Publish to PyPI, deploy versioned docs, push Docker image | `push` on tag `v*`                           |

> **Note:** Please keep this table up to date whenever workflows are added,
> renamed, or removed.
