#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

APP="src/App.tsx"
[[ -f "$APP" ]] || { echo "ERROR: $APP not found"; exit 1; }

cp "$APP" "$APP.before-page-fix"

python3 - <<'PY'
from pathlib import Path
p = Path('src/App.tsx')
s = p.read_text()

# Remove the broken fallback branch if it was inserted before useState.
lines = s.splitlines()
lines = [line for line in lines if line.strip() != 'if (page === "optimizer") return <Beta5Optimizer />;']
s = '\n'.join(lines) + ('\n' if s.endswith('\n') else '')

# Insert the branch immediately after page state is declared.
needle = 'const [page, setPage] = useState<Page>("dashboard");'
if 'if (page === "optimizer") return <Beta5Optimizer />;' not in s:
    if needle not in s:
        raise SystemExit('ERROR: Could not find page state declaration.')
    s = s.replace(
        needle,
        needle + '\n\n  if (page === "optimizer") return <Beta5Optimizer />;',
        1,
    )

p.write_text(s)
PY

npm run build
python3 -m compileall -q axiom
pytest -q

echo
echo "FIXED: optimizer page branch now runs after page state declaration."
echo "Backup: $APP.before-page-fix"
