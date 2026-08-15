#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/.." && pwd)"
local_dir="$project_root/.local"
template_dir="$project_root/docs/templates"

mkdir -p \
  "$local_dir/sessions/codex" \
  "$local_dir/sessions/cursor" \
  "$local_dir/sessions/other" \
  "$local_dir/derived"

initialize_file() {
  local target="$1"
  local template="$2"

  if [[ -e "$target" ]]; then
    printf 'exists: %s\n' "$target"
    return
  fi

  cp "$template" "$target"
  printf 'created: %s\n' "$target"
}

initialize_file \
  "$local_dir/AI_HISTORY.md" \
  "$template_dir/AI_HISTORY.template.md"
