#!/usr/bin/env bash
# Removes the desktop entry and the crosspatch:// association created by
# install.sh. Your mods, settings and this folder are left untouched.
set -euo pipefail

APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$APPS_DIR/crosspatch.desktop"

if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo "Removed $DESKTOP_FILE"
else
    echo "No desktop entry found at $DESKTOP_FILE - nothing to do."
fi

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" || true

echo
echo "Settings and mods were kept in ~/.config/CrossPatch."
echo "Delete that folder yourself if you want a clean slate."
