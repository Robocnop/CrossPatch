"""Rebuilds build/ctx, the Docker context of the Linux release, from the repo.

The context used to be assembled by hand, which shipped stale code once
(src/ not copied again after a change) and nearly shipped the Windows-only
UnRAR.exe. Rebuilding it from scratch every time makes both impossible.

Usage, from the repository root, after publishing the Linux parser:

    dotnet publish tools/CrossPatchParser/CrossPatchParser.csproj -c Release -f net8.0 \
        -r linux-x64 --self-contained true -p:PublishSingleFile=true \
        -p:InvariantGlobalization=true -o build/parser/linux-x64
    python packaging/stage_linux_ctx.py
    docker build --progress=plain --target export --output "type=local,dest=dist" build/ctx
"""

import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CTX = os.path.join(ROOT, "build", "ctx")
PARSER = os.path.join(ROOT, "build", "parser", "linux-x64", "CrossPatchParser")

# Windows-only files that must never reach the Linux archive.
WINDOWS_ONLY_ASSETS = {"UnRAR.exe"}
LINUX_SCRIPTS = ("run.sh", "install.sh", "uninstall.sh", "README-LINUX.md")


def _ignore(directory, names):
    return {n for n in names if n == "__pycache__" or n.endswith(".pyc")}


def main():
    if not os.path.isfile(PARSER):
        sys.exit(f"The Linux parser is missing: {PARSER}\nPublish it first (see the docstring).")

    if os.path.isdir(CTX):
        shutil.rmtree(CTX)
    os.makedirs(CTX)

    shutil.copytree(os.path.join(ROOT, "src"), os.path.join(CTX, "src"), ignore=_ignore)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(CTX, "assets"),
                    ignore=lambda d, names: {n for n in names if n in WINDOWS_ONLY_ASSETS})

    for name in ("requirements.txt", "LICENSE", "PRIVACY.md", "README.md", "version.txt"):
        shutil.copy2(os.path.join(ROOT, name), CTX)

    linux = os.path.join(ROOT, "packaging", "linux")
    for name in ("Dockerfile", "CrossPatch-linux.spec"):
        shutil.copy2(os.path.join(linux, name), CTX)
    os.makedirs(os.path.join(CTX, "linux"))
    for name in LINUX_SCRIPTS:
        shutil.copy2(os.path.join(linux, name), os.path.join(CTX, "linux", name))

    os.makedirs(os.path.join(CTX, "tools"))
    shutil.copy2(PARSER, os.path.join(CTX, "tools", "CrossPatchParser"))

    # A CRLF shebang fails with "bad interpreter" on Linux. .gitattributes
    # keeps these LF in git, but a copy edited on Windows could still slip in.
    for name in LINUX_SCRIPTS:
        with open(os.path.join(CTX, "linux", name), "rb") as f:
            if b"\r\n" in f.read():
                sys.exit(f"packaging/linux/{name} has CRLF line endings; convert it to LF.")

    print(f"Staged the Linux build context in {CTX}")


if __name__ == "__main__":
    main()
