# BroTab Agent Guide

## Overview
BroTab is a CLI tool for managing browser tabs (Firefox, Chrome/Chromium). It consists of a Python CLI, a native messaging mediator, and browser extensions.

## Core Architecture
- **CLI (`brotab/`)**: Primary user interface. `brotab/main.py` is the entry point.
- **Mediator (`brotab/mediator/`)**: A native messaging host that bridges the CLI and browser extensions. It communicates via JSON over stdin/stdout with the browser and provides an HTTP API for the CLI.
- **Extensions (`brotab/extension/`)**: Browser-side code (JS) that interacts with the `tabs` API.

## Native Messaging
- **Manifests**: Native messaging manifests are JSON files that tell the browser where the mediator executable is.
- **Installation**: `brotab install` creates these manifests in the appropriate browser-specific locations.
- **Communication**: The browser starts the mediator process and communicates with it using a length-prefixed JSON format over stdin/stdout.

## Development
- **Task Runner**: Use `just`. Run `just` to list available commands.
- **Python Environment**: Managed via `uv`. Use `uv sync --all-extras` to set up the development environment.
- **Testing**:
  - Unit tests: `pytest brotab/tests` (or `just unit-test`).
  - Smoke tests: `just smoke-test` (runs locally with mocked mediators).
  - Integration tests: `just integration-test` (runs in Docker via `brotab/tests/integration/Dockerfile`). Use `just integration-build` to build the image.

## Standards & Conventions
- **Python**: Follow `.pylintrc`. Use `uv` for dependency and environment management.
- **Version Management**: Version is defined in `brotab/__version__.py`.
- **Commits**: Follow existing style (concise, focus on "why").
- **Browser IDs**:
  - Chrome: `knldjmfmopnpolahpmmgbagdohdnhkik` (unpacked, derived from the `key` in the manifest), `mhpeahbikehnfkfnmopaigggliclhmnc` (Chrome Web Store).

## Critical Files
- `justfile`: Defines all major dev workflows.
- `pyproject.toml`: Project metadata and entry points.
- `brotab/mediator/brotab_mediator.py`: Core logic for browser communication.
- `brotab/tests/test_integration.py`: End-to-end validation logic.
