#!/usr/bin/env bash

usage() {
  cat <<EOF
Usage: $(basename "$0") [--no-tag] [VERSION]

Update the BroTab version in:
  - brotab/__version__.py
  - brotab/extension/chrome/manifest.json
  - brotab/extension/firefox/manifest.json

If VERSION is omitted, increment the patch component of the current version.
Creates a "Bump version to VERSION" commit.
Creates an annotated git tag named VERSION unless --no-tag is provided.
EOF
}

main() {
  local create_tag=1
  local repo_root
  local current_version
  local version

  while [[ $# -gt 0 ]]
  do
    case "$1" in
      --no-tag)
        create_tag=0
        shift
        ;;
      -h|--help)
        usage
        return 0
        ;;
      --)
        shift
        break
        ;;
      -*)
        echo "Unknown option: $1" >&2
        usage >&2
        return 2
        ;;
      *)
        break
        ;;
    esac
  done

  if [[ $# -gt 1 ]]
  then
    usage >&2
    return 2
  fi

  repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "Must be run from inside the brotab git repository" >&2
    return 2
  }

  current_version="$(python3 - <<'PY' "$repo_root"
import pathlib
import re
import sys

version_file = pathlib.Path(sys.argv[1]) / "brotab" / "__version__.py"
match = re.search(r"^__version__ = ['\"]([^'\"]+)['\"]$", version_file.read_text(encoding="utf-8"), re.MULTILINE)
if match is None:
    raise SystemExit(f"Could not read version from {version_file}")
print(match.group(1))
PY
)"

  version="${1:-}"
  if [[ -z "${version:-}" ]]
  then
    version="$(python3 - <<'PY' "$current_version"
import sys

parts = sys.argv[1].split(".")
if len(parts) != 3 or any(not part.isdigit() for part in parts):
    raise SystemExit(f"Current version is not a semantic version with numeric major.minor.patch parts: {sys.argv[1]}")
major, minor, patch = (int(part) for part in parts)
print(f"{major}.{minor}.{patch + 1}")
PY
)"
  fi

  if [[ "$version" == "$current_version" ]]
  then
    echo "Version is already $version" >&2
    return 2
  fi

  if [[ "$create_tag" -eq 1 ]] && git -C "$repo_root" rev-parse --verify --quiet "refs/tags/$version" >/dev/null
  then
    echo "Git tag $version already exists" >&2
    return 2
  fi

  python3 - <<'PY' "$repo_root" "$version"
import json
import pathlib
import re
import sys

repo_root = pathlib.Path(sys.argv[1])
version = sys.argv[2]

version_file = repo_root / "brotab" / "__version__.py"
chrome_manifest = repo_root / "brotab" / "extension" / "chrome" / "manifest.json"
firefox_manifest = repo_root / "brotab" / "extension" / "firefox" / "manifest.json"

version_text = version_file.read_text(encoding="utf-8")
updated_text, count = re.subn(
    r"^__version__ = ['\"][^'\"]+['\"]$",
    f"__version__ = '{version}'",
    version_text,
    count=1,
    flags=re.MULTILINE,
)
if count != 1:
    raise SystemExit(f"Could not update version in {version_file}")
version_file.write_text(updated_text, encoding="utf-8")

for manifest_path in (chrome_manifest, firefox_manifest):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = version
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

  git -C "$repo_root" add \
    brotab/__version__.py \
    brotab/extension/chrome/manifest.json \
    brotab/extension/firefox/manifest.json
  git -C "$repo_root" commit --only -m "Bump version to $version" -- \
    brotab/__version__.py \
    brotab/extension/chrome/manifest.json \
    brotab/extension/firefox/manifest.json

  if [[ "$create_tag" -eq 1 ]]
  then
    git -C "$repo_root" tag -a "$version" -m "$version"
    printf 'Bumped version from %s to %s, committed, and tagged %s\n' \
      "$current_version" "$version" "$version"
    return 0
  fi

  printf 'Bumped version from %s to %s and committed without tagging\n' \
    "$current_version" "$version"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]
then
  main "$@"
fi

# vim: set ft=sh ts=2 sw=2 et:
