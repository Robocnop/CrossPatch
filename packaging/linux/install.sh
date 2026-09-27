#!/usr/bin/env bash
# Registers CrossPatch with your desktop: an application entry in the menu and
# the crosspatch:// links GameBanana's "1-Click Install" button uses.
#
# Nothing is copied anywhere and no root access is needed - the entry points at
# this folder, so keep it where it is (or re-run this script after moving it).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$APPS_DIR/crosspatch.desktop"

chmod +x "$HERE/CrossPatch" "$HERE/run.sh" 2>/dev/null || true
[ -f "$HERE/tools/CrossPatchParser" ] && chmod +x "$HERE/tools/CrossPatchParser" 2>/dev/null || true

mkdir -p "$APPS_DIR"

# Exec= has its own quoting rules: the path is double-quoted, and inside the
# quotes a backslash, ", ` and $ are escaped (with every escaping backslash
# doubled once more by the file format), and % becomes %%. Without this a
# folder with a space in its name broke both the menu entry and 1-Click.
EXEC_PATH=$(printf '%s' "$HERE/run.sh" | sed -e 's/\\/\\\\\\\\/g' -e 's/["`$]/\\\\&/g' -e 's/%/%%/g')

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=CrossPatch
GenericName=Crossworlds Mod Manager
Comment=Mod manager for Sonic Racing: CrossWorlds
Exec="$EXEC_PATH" %u
Icon=$HERE/assets/CrossP.png
Terminal=false
Categories=Game;Utility;
MimeType=x-scheme-handler/crosspatch;
StartupWMClass=CrossPatch
DESKTOP

chmod +x "$DESKTOP_FILE"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" || true
command -v xdg-mime >/dev/null 2>&1 && xdg-mime default crosspatch.desktop x-scheme-handler/crosspatch || true

echo "CrossPatch installed for the current user."
echo "  menu entry : $DESKTOP_FILE"
echo "  crosspatch:// links now open CrossPatch (1-Click Install from GameBanana)."
echo
echo "Run ./uninstall.sh to undo this. It does not delete this folder."
