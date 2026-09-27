#!/usr/bin/env bash
# Starts CrossPatch from wherever this folder happens to live.
# Some graphical archive managers drop the executable bit when they unpack a
# zip, so restore it here instead of leaving people with "Permission denied".
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

chmod +x "$HERE/CrossPatch" 2>/dev/null || true
[ -f "$HERE/tools/CrossPatchParser" ] && chmod +x "$HERE/tools/CrossPatchParser" 2>/dev/null || true

exec "$HERE/CrossPatch" "$@"
