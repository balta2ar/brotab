set shell := ["bash", "-cu"]

default:
  @just --list

unit-test:
  uv run pytest -v

build:
  rm -rf ./dist
  uv build

smoke-test: build
  uv pip install --force-reinstall dist/*.whl
  uv run python -c 'from brotab.tests.test_main import run_mocked_mediators as run; run(count=3, default_port_offset=0, delay=0)' & \
  sleep 3 && \
  uv run brotab list && \
  uv run brotab windows && \
  uv run brotab clients && \
  uv run brotab active && \
  uv run brotab words && \
  uv run brotab text && \
  uv run brotab html

integration-build:
  docker build -t brotab-integration -f brotab/tests/integration/Dockerfile .

integration-test:
  INTEGRATION_TEST=1 uv run pytest -v -k test_integration -s

test-all: unit-test smoke-test integration-test
  @echo "Testing all"

sign-firefox-addon:
  ./scripts/sign-firefox-addon.sh

package-browser-artifacts:
  ./scripts/package-browser-artifacts.sh

package-chrome-crx:
  ./scripts/package-chrome-crx.sh

reset:
  pkill python3 || true
  pkill xvfb-run || true
  pkill node || true
  pkill Xvfb || true
  pkill firefox || true
