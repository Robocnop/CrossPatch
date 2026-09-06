# CrossPatch - A Crossworlds Mod Manager.

DISCLAIMER: AI was used in the assistance of making this program. 
While most of it is human there's also a lot of AI code, because this program needed to do some complicated stuff I can't wrap my head around


# What is CrossPatch?
CrossPatch is an easy to use mod manager for Sonic Racing: Crossworlds

## Features:
- Automatic Game Detection
- Automatic folder creation, no need to set up your ~mods folder in the game files
- Supports both Pak and UE4SS mods
- Support for custom mod display names, authors, version numbers, updating etc.
- Mod profiles, and shareable ones: export your setup to a file that rebuilds
  itself on someone else's install
- Simple, Clean, and easy to use UI
- Ability to launch the game via CrossPatch
- Functions on both Windows and Linux
- English and French interface, picked automatically from your system language

### Archive Support
CrossPatch supports extracting `.zip`, `.7z`, and `.rar` archives.

For `.7z` and `.rar` support, you may need to install additional tools:
- **.7z Support**: Provided by the `py7zr` Python package, which is installed automatically.
- **.rar Support**: CrossPatch can use a bundled `unrar` tool or a system-wide installation.
  - **Recommended (Bundled)**: Download the command-line tool from the official WinRAR website. Place `UnRAR.exe` (for Windows) or `unrar` (for Linux) inside the `assets` folder next to the CrossPatch executable.
  - **Alternative (System-wide)**: If the bundled tool is not found, CrossPatch will look for `unrar` in your system's PATH.
    - **Windows**: Install WinRAR and ensure its folder is in your PATH.
    - **Linux**: Install the `unrar` package via your distribution's package manager (e.g., `sudo apt install unrar` or `sudo dnf install unrar`).

### Where your mods are stored

On first launch CrossPatch offers a default folder and creates it for you:

- **Windows**: `%APPDATA%\CrossPatch\mods`
- **Linux**: `~/.config/CrossPatch/mods`

You can pick a different one from that dialog, or later under **Settings > Mods Folder**.
This is *not* your game's `~mods` folder — CrossPatch copies the enabled mods into the
game itself when you apply or launch.

If you set `CROSSPATCH_PORTABLE=1`, the mods folder is `mods/` next to the executable instead.

### Sharing a profile

A profile is a set of mods, the order they load in and which of them are on.
**Settings > Profile** has an export and an import button next to the profile
picker.

Exporting writes a small `.crosspatch` file. It holds the list of mods, their
GameBanana pages and your load order, nothing else: no mod files are copied, so
the file stays a few kilobytes and nobody's work gets redistributed.

Importing one creates a new profile, downloads every mod it lists that you do
not already have, and switches to it. Mods you already own are recognised by
their GameBanana page, whatever you called their folder, so nothing is
downloaded twice. If a submission offers several archives and the profile does
not say which one was used, CrossPatch asks rather than guessing.

Two things a shared profile cannot do:

- A mod its author installed by hand has no GameBanana page recorded, so there
  is nothing to download it from. Those are listed as **No download link** and
  left out; you have to find them yourself.
- A mod whose page has since been taken down is reported at the end of the
  import instead of failing quietly.

### Languages

CrossPatch ships in **English** and **French**. On first launch it follows your
system language: a French Windows starts in French, anything else falls back to
English. You can force a language under **Settings > Language**; the change
applies after a restart.

**Adding your own language**

1. Copy `assets/locales/en.json`.
2. Rename it to your language code: `de.json`, `es.json`, `pt_BR.json`...
3. Translate the values (leave the keys on the left alone) and set `_meta.name`
   to the language's own name - that is what the picker displays.
4. Drop it in:
   - Windows: `%APPDATA%\CrossPatch\locales\`
   - Linux: `~/.config/CrossPatch/locales/`

Restart CrossPatch and your language appears in the list. Files in that folder
override the bundled ones, so you can also fix a wording in `fr.json` without
touching the install - and it survives updates. Any key you leave out falls back
to English, so a partial translation works fine.

Pull requests adding a language to `assets/locales/` are welcome.

## Misc Info

It is HIGHLY recommended that you run CrossPatch as an Admin or you are a Local Admin on your device. Not being an admin can inhibit CrossPatch from setting up your mods correctly and cause issues.

For setting up custom display names, authors and version to support CrossPatch, you just need to create a file named "info.json" in your mod folder

Below is a template you can use. The `mod_type` field is optional and defaults to `"pak"`. Use `"ue4ss-script"` for UE4SS script mods, or `"ue4ss-logic"` for UE4SS logic mods.

```json
{
  "name": "YOUR MOD NAME",
  "version": "1.0",
  "author": "Your Name",
  "mod_page": "https://gamebanana.com/mods/12345",
  "mod_type": "pak" 
}
```

## Privacy and Security

CrossPatch is designed to be safe and transparent.

### Privacy Policy

The application does not collect or transmit any personal user data. For more details, please see our [Privacy Policy](PRIVACY.md).

### Code Signing Policy

To improve security and user trust, our official releases are signed.

*   Free code signing provided by [SignPath.io](https://signpath.io), certificate by SignPath Foundation.
*   **Committers and Reviewers**: [NockCS](https://github.com/NickPlayzGITHUB), [RED1](https://github.com/Red1Fouad), [AntiApple4life](https://github.com/AntiApple4life), [Ben Thalmann](https://github.com/btdotdev)
*   **Approvers**: [NockCS](https://github.com/NickPlayzGITHUB)
```
