# Contributing to CrossPatch

Thanks for wanting to help. CrossPatch is a mod manager for *Sonic Racing: CrossWorlds*,
written in Python with PySide6 (Qt6), with a small C# helper for reading `.pak` files.
It is GPL-3.0, and every kind of contribution is welcome: bug reports, translations,
documentation, and code.

If you are unsure whether an idea fits, open an issue first and ask. That is
cheaper for everyone than a large pull request that has to be rewritten.

## Table of contents

- [Reporting a bug](#reporting-a-bug)
- [Running from source](#running-from-source)
- [Where things live](#where-things-live)
- [Adding or fixing a translation](#adding-or-fixing-a-translation)
- [Writing code](#writing-code)
- [Testing your change](#testing-your-change)
- [Pull requests](#pull-requests)

## Reporting a bug

Good reports get fixed faster. Please include:

- Your operating system, and for Linux your distribution and desktop session.
- The CrossPatch version, shown in the title bar and in the credits window.
- What you expected, and what happened instead.
- The console log. Turn it on under **Settings > Show console logs**, restart
  CrossPatch, reproduce the problem, then copy what the console printed.

If the problem involves a specific mod, a link to its GameBanana page helps a lot.

## Running from source

You need Python. The releases are built with Python 3.12 on Linux and 3.14 on
Windows, so anything in that range is safe.

```bash
git clone https://github.com/Robocnop/CrossPatch
cd CrossPatch
pip install -r requirements.txt
python src/Main.py
```

You do **not** need the .NET SDK. The `.pak` analyser is committed already built,
under `tools/CrossPatchParser/bin/Release/net8.0/publish/`, and `src/PakInspector.py`
finds it there automatically. You only need .NET if you are changing the analyser
itself, in which case `./build_parser.sh` republishes it.

Two environment variables are useful while developing:

| Variable | Effect |
|---|---|
| `CROSSPATCH_PORTABLE=1` | Keeps config and mods next to the working directory instead of in your user profile, so you do not pollute your real setup |
| `CROSSPATCH_DISABLE_UPDATES=1` | Skips the update check on startup |

Running from source already skips the updater, so it can never overwrite your
working copy with a release build.

## Where things live

| Path | What it is |
|---|---|
| `src/` | The application. `Main.py` is the entry point, `CrossPatch.py` holds the main window |
| `src/Util.py` | Shared helpers: archives, GameBanana API, conflict detection |
| `src/Config.py` | Settings, config directory, game folder detection |
| `src/Updater.py` | The in-app updater |
| `assets/locales/` | Interface translations |
| `assets/themes/` | Qt stylesheets |
| `tools/CrossPatchParser/` | The C# `.pak` analyser |

Your settings and mods are **not** in the repository. They live in
`%APPDATA%\CrossPatch` on Windows and `~/.config/CrossPatch` on Linux.

## Adding or fixing a translation

This is the easiest way to contribute, and it needs no Python at all.

1. Copy `assets/locales/en.json`.
2. Rename it to your language code, for example `de.json`, `es.json` or `pt_BR.json`.
3. Translate the values on the right. Leave the keys on the left untouched.
4. Set `_meta.name` to the language's own name, since that is what the picker shows.
5. Open a pull request adding the file to `assets/locales/`.

Any key you leave out falls back to English, so a partial translation is still
useful. To test without rebuilding, drop your file in `%APPDATA%\CrossPatch\locales\`
or `~/.config/CrossPatch/locales/`, which overrides the bundled ones.

If you add a new string to the interface, add the key to **every** file in
`assets/locales/`, not just `en.json`.

## Writing code

There is no linter and no formatter config, so match the surrounding code rather
than any external style guide. A few things the project does care about:

**Never swallow an error the user needs to know about.** This codebase has been
bitten repeatedly by failures that were caught, ignored, and left the user
staring at a screen that silently did nothing. If something fails in a way that
changes what the user gets, say so, either with a message box or at minimum a
`print` that reaches the console log.

**Comments explain why, not what.** The code already says what it does. A comment
earns its place when it records a reason, a constraint, or a trap that the next
reader would otherwise walk into. Look at `Config.py` and `Util.py` for the
density expected.

**All user facing text goes through `tr()`.** Never hardcode an English string in
the interface. Add the key to `assets/locales/en.json` and `fr.json`.

**Watch file encoding.** On Windows, `open(path, 'w')` writes cp1252 by default,
which quietly corrupts any non ASCII character. Always pass `encoding='utf-8'`
when you read or write text.

**Mind both platforms.** Anything touching paths, processes or archives runs on
Windows and Linux. Use `os.path.join`, never a hardcoded separator, and remember
that Linux is case sensitive.

## Testing your change

There is no automated test suite yet, so testing is manual. Before opening a
pull request, please check at least:

- CrossPatch starts, and the mod list loads.
- Enabling and disabling a mod still writes to the game folder correctly.
- Whatever you touched, in the case it was written for and in one case where it
  should fail.

If your change touches the **updater, archive extraction, or path handling**,
test it on both Windows and Linux if you can, and say in the pull request which
ones you actually tested. Those three areas are where the platform differences
bite, and they have caused silent breakage before. Test archive handling against
a real release zip rather than one you made yourself, since the layout of the
real archives has its own quirks.

## Pull requests

- Branch off `main` and keep one pull request to one topic. A translation, a bug
  fix and a refactor should be three pull requests, not one.
- Do not commit build output. `dist/` and `build/` are ignored, and the committed
  analyser binaries under `tools/CrossPatchParser/bin/` should be left alone
  unless you deliberately rebuilt the analyser. Republishing it over those paths
  turns a small diff into several hundred files.
- Do not bump the version. `version.txt` and `src/Constants.py` are changed when
  a release is cut, not in feature pull requests.
- Write a description that says what the problem was, not only what you changed.
  If you fixed something subtle, explain how it failed, so the next person does
  not undo it.

By contributing, you agree that your work is licensed under GPL-3.0, the same as
the rest of the project.
