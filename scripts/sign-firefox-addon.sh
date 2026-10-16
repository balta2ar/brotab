#!/usr/bin/env bash

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Sign the Firefox BroTab extension for self-distribution.

Required environment:
  WEB_EXT_API_KEY       Mozilla Add-ons API JWT issuer key
  WEB_EXT_API_SECRET    Mozilla Add-ons API JWT secret

Options:
  --source-dir PATH     Extension source directory
  --artifacts-dir PATH  Output directory for signed artifacts
  --amo-metadata PATH   Metadata JSON for listed AMO submissions
  --approval-timeout MS How long web-ext waits for AMO approval
  --api-key KEY         Override WEB_EXT_API_KEY
  --api-secret SECRET   Override WEB_EXT_API_SECRET
  --channel CHANNEL     Signing channel (default: unlisted/self-distributed)
  --manifest-version VERSION
                       Override manifest.json version before signing
  -h, --help            Show this help
EOF
}

main() {
  local repo_root
  local source_dir
  local artifacts_dir
  local amo_metadata
  local api_key
  local api_secret
  local approval_timeout
  local channel
  local manifest_version
  local signing_source_dir
  local temp_source_dir

  repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "Must be run from inside the brotab git repository" >&2
    return 2
  }

  source_dir="${repo_root}/brotab/extension/firefox"
  artifacts_dir="${repo_root}/dist/firefox-signed"
  amo_metadata=""
  api_key="${WEB_EXT_API_KEY:-}"
  api_secret="${WEB_EXT_API_SECRET:-}"
  approval_timeout=""
  channel="unlisted"
  manifest_version=""
  temp_source_dir=""

  while [[ -n "${1:-}" ]]
  do
    case "$1" in
      --source-dir)
        source_dir="$2"
        shift 2
        ;;
      --artifacts-dir)
        artifacts_dir="$2"
        shift 2
        ;;
      --amo-metadata)
        amo_metadata="$2"
        shift 2
        ;;
      --approval-timeout)
        approval_timeout="$2"
        shift 2
        ;;
      --api-key)
        api_key="$2"
        shift 2
        ;;
      --api-secret)
        api_secret="$2"
        shift 2
        ;;
      --channel)
        channel="$2"
        shift 2
        ;;
      --manifest-version)
        manifest_version="$2"
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

  if [[ -z "${api_key:-}" ]]
  then
    echo "WEB_EXT_API_KEY is required" >&2
    return 2
  fi

  if [[ -z "${api_secret:-}" ]]
  then
    echo "WEB_EXT_API_SECRET is required" >&2
    return 2
  fi

  if [[ ! -d "$source_dir" ]]
  then
    echo "Extension source directory not found: $source_dir" >&2
    return 2
  fi

  mkdir -p "$artifacts_dir"

  signing_source_dir="$source_dir"

  if [[ -n "${manifest_version:-}" ]]
  then
    temp_source_dir="$(mktemp -d)"
    cp -R "$source_dir/." "$temp_source_dir/"

    python3 - <<'PY' "$temp_source_dir/manifest.json" "$manifest_version"
import json
import pathlib
import sys

manifest_path = pathlib.Path(sys.argv[1])
version = sys.argv[2]
manifest = json.loads(manifest_path.read_text())
manifest["version"] = version
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
PY

    signing_source_dir="$temp_source_dir"
  fi

  export WEB_EXT_API_KEY="$api_key"
  export WEB_EXT_API_SECRET="$api_secret"

  local -a web_ext_args
  web_ext_args=(
    sign
    --source-dir "$signing_source_dir"
    --artifacts-dir "$artifacts_dir"
    --channel "$channel"
    --ignore-files 'readme.txt'
    --no-input
  )

  if [[ -n "${amo_metadata:-}" && "$channel" != "unlisted" && -f "$amo_metadata" ]]
  then
    web_ext_args+=(--amo-metadata "$amo_metadata")
  fi

  if [[ -n "${approval_timeout:-}" ]]
  then
    web_ext_args+=(--approval-timeout "$approval_timeout")
  fi

  web-ext "${web_ext_args[@]}"
  local status=$?

  if [[ -n "${temp_source_dir:-}" ]]
  then
    rm -rf "$temp_source_dir"
  fi

  return "$status"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]
then
  main "$@"
fi

# vim: set ft=sh ts=2 sw=2 et:
