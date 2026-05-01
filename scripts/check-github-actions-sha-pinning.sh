#!/usr/bin/env bash
set -euo pipefail

failed=0
has_rg=0
if command -v rg >/dev/null 2>&1; then
  has_rg=1
fi

# Check GitHub workflow and composite action files.
while IFS= read -r -d '' file; do
  while IFS=: read -r line_no line_text; do
    uses_ref=$(echo "$line_text" | sed -E 's/^[[:space:]-]*uses:[[:space:]]*([^[:space:]#]+).*$/\1/')

    # Allow local actions/workflows.
    if [[ "$uses_ref" == ./* ]]; then
      continue
    fi

    # Allow reusable workflows by tag/branch as an explicit exception.
    if [[ "$uses_ref" =~ ^[^[:space:]@]+/[^[:space:]@]+/\.github/workflows/[^@]+@[^[:space:]#]+$ ]]; then
      continue
    fi

    # Allow container actions.
    if [[ "$uses_ref" == docker://* ]]; then
      continue
    fi

    # External actions must be pinned to a full-length SHA.
    if [[ ! "$uses_ref" =~ @[0-9a-f]{40}$ ]]; then
      echo "ERROR: ${file}:${line_no} uses '${uses_ref}' and is not pinned to a full-length commit SHA."
      failed=1
    fi
  done < <(
    if [[ "$has_rg" -eq 1 ]]; then
      rg -n '^\s*-?\s*uses:\s*' "$file"
    else
      grep -nE '^[[:space:]]*-?[[:space:]]*uses:[[:space:]]*' "$file" || true
    fi
  )
done < <(find .github/workflows .github/actions -type f \( -name '*.yml' -o -name '*.yaml' \) -print0)

if [[ "$failed" -ne 0 ]]; then
  echo
  echo "Fix: replace action refs like @v4/@main with @<40-char-sha>."
  echo "Exception: reusable workflow refs under .github/workflows may remain tag-based."
  exit 1
fi

exit 0