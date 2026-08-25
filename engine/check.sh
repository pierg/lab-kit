#!/usr/bin/env bash
# The lab gate: form lint (shell contract) + ladder lint (every number traces) + book verify.
# Identical locally and in CI — that is the point. Fail-loud, seconds-fast, no network.
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
LAB_ROOT="${LAB_ROOT:-$(cd "$KIT/.." && pwd)}"
export LAB_ROOT
cd "$LAB_ROOT"

python3 "$KIT/engine/lint.py"
python3 "$KIT/tools/ladder_lint.py"

# Books are optional; verify each one that exists.
CONTENT_DIR="$(python3 -c "
import json,pathlib
p = pathlib.Path('lab.json')
print(json.loads(p.read_text())['content'] if p.is_file() else 'content')
" 2>/dev/null || echo content)"
if [ -d "$CONTENT_DIR/books" ] && command -v node >/dev/null 2>&1; then
  for book in "$CONTENT_DIR"/books/*/; do
    [ -f "$book/index.html" ] || continue
    node "$KIT/engine/verify_book.mjs" "$book"
  done
fi

echo "check ok"
