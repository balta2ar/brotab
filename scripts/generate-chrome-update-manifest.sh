#!/usr/bin/env bash

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Generate a Chrome update manifest XML file for self-hosted CRX updates.

Options:
  --extension-id ID   Chrome extension ID (appid)
  --version VALUE     Extension version
  --codebase-url URL  HTTPS URL to the CRX download
  --output PATH       Output XML file path
  -h, --help          Show this help
EOF
}

main() {
  local codebase_url
  local extension_id
  local output
  local version

  codebase_url=""
  extension_id=""
  output=""
  version=""

  while [[ -n "${1:-}" ]]
  do
    case "$1" in
      --extension-id)
        extension_id="$2"
        shift 2
        ;;
      --version)
        version="$2"
        shift 2
        ;;
      --codebase-url)
        codebase_url="$2"
        shift 2
        ;;
      --output)
        output="$2"
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

  if [[ -z "${extension_id:-}" || -z "${version:-}" || -z "${codebase_url:-}" || -z "${output:-}" ]]
  then
    echo "extension-id, version, codebase-url, and output are required" >&2
    usage >&2
    return 2
  fi

  mkdir -p "$(dirname "$output")"

  cat > "$output" <<EOF
<?xml version='1.0' encoding='UTF-8'?>
<gupdate xmlns='http://www.google.com/update2/response' protocol='2.0'>
  <app appid='${extension_id}'>
    <updatecheck codebase='${codebase_url}' version='${version}' />
  </app>
</gupdate>
EOF
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]
then
  main "$@"
fi

# vim: set ft=sh ts=2 sw=2 et:
