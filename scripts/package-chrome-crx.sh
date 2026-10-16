#!/usr/bin/env bash

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Package the Chrome extension as a CRX.

Options:
 --crx3-bin PATH     crx3 binary to use for packaging
 --chrome-bin PATH   Deprecated alias accepted for compatibility
 --key-file PATH     PEM private key for stable CRX packaging
 --no-pem-output     Do not write a PEM file into the output directory
  --output-dir PATH   Output directory for the CRX artifact
  --update-url URL    Set update_url in the packaged manifest
  --version VALUE     Version string used in filenames
  -h, --help          Show this help
EOF
}

find_crx3_bin() {
  local candidate

  for candidate in \
    "${CRX3_BIN:-}" \
    crx3
  do
    if [[ -n "${candidate:-}" ]] && command -v "$candidate" >/dev/null 2>&1
    then
      command -v "$candidate"
      return 0
    fi
  done

  echo "Could not find a crx3 binary" >&2
  return 2
}

strip_manifest_key() {
  local manifest_path="$1"

  python3 - <<'PY' "$manifest_path"
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text())
data.pop("key", None)
path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

set_manifest_update_url() {
  local manifest_path="$1"
  local update_url="$2"

  python3 - <<'PY' "$manifest_path" "$update_url"
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
update_url = sys.argv[2]
data = json.loads(path.read_text())
data["update_url"] = update_url
path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

main() {
  local crx3_bin
  local extension_source
  local key_file
  local output_crx
  local output_dir
  local output_pem
  local pem_output
  local repo_root
  local temp_dir
  local temp_extension_dir
  local temp_extension_zip
  local update_url
  local version

  repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "Must be run from inside the brotab git repository" >&2
    return 2
  }

  crx3_bin=""
  extension_source="${repo_root}/brotab/extension/chrome"
  key_file=""
  output_dir="${repo_root}/dist/browser"
  pem_output=1
  update_url=""
  version=""

  while [[ -n "${1:-}" ]]
  do
    case "$1" in
      --crx3-bin)
        crx3_bin="$2"
        shift 2
        ;;
      --chrome-bin)
        crx3_bin="$2"
        shift 2
        ;;
      --key-file)
        key_file="$2"
        shift 2
        ;;
      --output-dir)
        output_dir="$2"
        shift 2
        ;;
      --update-url)
        update_url="$2"
        shift 2
        ;;
      --no-pem-output)
        pem_output=""
        shift
        ;;
      --version)
        version="$2"
        shift 2
        ;;
      -h|--help)
        usage
        return 0
        ;;
      *)
        echo "Unknown argument: $1" >&2
        usage >&2
        return 2
        ;;
    esac
  done

  if [[ -z "${version:-}" ]]
  then
    version="$(
      python3 - <<'PY'
from brotab.__version__ import __version__
print(__version__)
PY
    )"
  fi

  if [[ ! -d "$extension_source" ]]
  then
    echo "Chrome extension source directory not found: $extension_source" >&2
    return 2
  fi

  if [[ -n "${key_file:-}" ]] && [[ ! -f "$key_file" ]]
  then
    echo "Chrome extension key file not found: $key_file" >&2
    return 2
  fi

  if [[ -n "${crx3_bin:-}" ]]
  then
    if ! command -v "$crx3_bin" >/dev/null 2>&1
    then
      echo "crx3 binary not found: $crx3_bin" >&2
      return 2
    fi

    crx3_bin="$(command -v "$crx3_bin")"
  else
    crx3_bin="$(find_crx3_bin)"
  fi

  mkdir -p "$output_dir"
  output_crx="${output_dir}/brotab-chrome-${version}.crx"
  output_pem="${output_dir}/brotab-chrome-${version}.pem"

  temp_dir="$(mktemp -d)"
  trap 'rm -rf "$temp_dir"' EXIT
  temp_extension_dir="${temp_dir}/chrome"
  temp_extension_zip="${temp_dir}/chrome.zip"

  cp -R "$extension_source" "$temp_extension_dir"
  chmod -R +w "$temp_extension_dir"
  strip_manifest_key "${temp_extension_dir}/manifest.json"
  if [[ -n "${update_url:-}" ]]
  then
    set_manifest_update_url "${temp_extension_dir}/manifest.json" "${update_url}"
  fi

  # Normalize mtimes so the ZIP fed to crx3 is reproducible across environments.
  find "$temp_extension_dir" -exec touch -h -d '1980-01-01 00:00:00Z' {} +

  (
    cd "$temp_extension_dir"
    find . -type f | LC_ALL=C sort | zip -X -q "$temp_extension_zip" -@
  )

  if [[ -n "${key_file:-}" ]]
  then
    "$crx3_bin" pack "$temp_extension_zip" --pem "$key_file" --outfile "$output_crx"
  else
    "$crx3_bin" keygen "${temp_dir}/generated-key.pem" >/dev/null
    "$crx3_bin" pack "$temp_extension_zip" --pem "${temp_dir}/generated-key.pem" --outfile "$output_crx"
  fi

  if [[ ! -f "$output_crx" ]]
  then
    echo "crx3 did not produce a CRX file" >&2
    return 1
  fi

  if [[ -n "${pem_output:-}" ]]
  then
    if [[ -n "${key_file:-}" ]]
    then
      cp -f "$key_file" "$output_pem"
    elif [[ -f "${temp_dir}/generated-key.pem" ]]
    then
      cp -f "${temp_dir}/generated-key.pem" "$output_pem"
    fi
  fi

  echo "Created $output_crx"

  if [[ -n "${pem_output:-}" ]] && [[ -f "$output_pem" ]]
  then
    echo "Created $output_pem"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]
then
  main "$@"
fi

# vim: set ft=sh ts=2 sw=2 et:
