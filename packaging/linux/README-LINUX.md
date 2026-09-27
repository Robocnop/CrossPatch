# CrossPatch for Linux (x86-64)

A mod manager for **Sonic Racing: CrossWorlds**. This is the Linux build; it
contains everything it needs, so there is nothing to compile and no Python or
.NET to install.

---

## Quick start

```bash
unzip CrossPatch-*-linux-x64.zip
cd CrossPatch
./run.sh
```

`run.sh` restores the executable bit (graphical archive managers often drop it)
and starts the app. If you prefer, `./CrossPatch` works just as well once the
bit is set.

To get a menu entry and make GameBanana's **1-Click Install** buttons open
CrossPatch, run this once:

```bash
./install.sh
```

It writes a single desktop entry to `~/.local/share/applications/` pointing at
this folder — nothing is copied elsewhere and no root access is needed. Keep the
folder where it is, or re-run `install.sh` after moving it. `./uninstall.sh`
undoes it and leaves your mods and settings alone.

---

## What you need

The build targets glibc 2.31, so anything from **Ubuntu 20.04 / Debian 11 /
Fedora 33 / Arch / SteamOS 3 (Steam Deck)** onwards will run it.

Qt needs a handful of graphics libraries that every desktop install already
has. Only a very minimal system would be missing them:

| Distro | Command |
|---|---|
| Debian / Ubuntu / Mint | `sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libgl1 libegl1 libfontconfig1` |
| Fedora | `sudo dnf install xcb-util-cursor libxkbcommon-x11 mesa-libGL fontconfig` |
| Arch / SteamOS | `sudo pacman -S --needed xcb-util-cursor libxkbcommon-x11 libglvnd fontconfig` |

Optional, for `.rar` mods only: install `unrar` from your package manager, or
drop an `unrar` binary in the `assets/` folder next to CrossPatch.

**.NET is not required.** The pak analyser (`tools/CrossPatchParser`) is a
self-contained .NET 8 build, so the "install .NET 8" prompt you may have read
about does not appear on this package.

---

## Where things live

| | |
|---|---|
| Settings | `~/.config/CrossPatch/config.json` |
| Your mods | `~/.config/CrossPatch/mods` |
| Extra languages | `~/.config/CrossPatch/locales/` |

Set `CROSSPATCH_PORTABLE=1` to keep all of that next to the executable instead:

```bash
CROSSPATCH_PORTABLE=1 ./run.sh
```

The mods folder is **not** the game's `~mods` folder — CrossPatch copies the
enabled mods into the game when you apply or launch.

---

## The game folder

CrossPatch looks for the game at:

```
~/.local/share/Steam/steamapps/common/SonicRacingCrossWorlds
```

If you installed it on another drive or through Flatpak, auto-detection fails
and CrossPatch asks you to point at the folder yourself. Common alternatives:

```
~/.steam/steam/steamapps/common/SonicRacingCrossWorlds
/run/media/<user>/<drive>/steamapps/common/SonicRacingCrossWorlds     # Steam Deck SD card
~/.var/app/com.valvesoftware.Steam/data/Steam/steamapps/common/...    # Flatpak Steam
```

The game itself runs through Proton — that is Steam's business, not
CrossPatch's. The mods are plain files and go into the same place they do on
Windows.

**Launch Game** shells out to `steam steam://rungameid/2486820`, so the `steam`
command has to be on your `PATH`. On a Flatpak-only Steam install, start the
game from Steam instead.

---

## Languages

Ships with English and French, picked from your system locale, and switchable
under **Settings > Language**. To add your own, copy
`assets/locales/en.json`, translate the values, set `_meta.name` to the
language's own name, and drop it in `~/.config/CrossPatch/locales/` as
`<code>.json` (`de.json`, `es.json`, `pt_BR.json`...). It survives updates and
needs no rebuild.

---

## Troubleshooting

**`Permission denied`** — the archive manager dropped the executable bit:
`chmod +x CrossPatch run.sh install.sh uninstall.sh tools/CrossPatchParser`

**Nothing happens / no window** — start it from a terminal to see the errors:
`./run.sh`

**`could not load the Qt platform plugin "xcb"`** — install the packages from
the table above; `QT_DEBUG_PLUGINS=1 ./run.sh` names the missing library.

**Wayland session issues** — force X11 (XWayland handles it fine):
`QT_QPA_PLATFORM=xcb ./run.sh`

**Conflict detection reports nothing** — check the analyser runs:
`./tools/CrossPatchParser --help`

Bugs and questions: https://github.com/Robocnop/CrossPatch/issues

---

CrossPatch is GPL-3.0. See `LICENSE`. `README.md` covers the features shared
with the Windows build.
