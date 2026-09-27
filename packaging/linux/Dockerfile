# CrossPatch Linux release build.
#
# Stage 1 runs PyInstaller on bullseye (glibc 2.31), so the binary runs on
# Ubuntu 20.04+ / Debian 11+ / SteamOS. Qt's runtime libraries are installed
# here even though nothing displays: without them PyInstaller cannot import
# PySide6 to ask where its plugins live, silently collects no platform plugin,
# and the finished app dies with 'could not load the Qt platform plugin "xcb"'
# on every machine. The build would still report success, so the layout is
# asserted below instead of trusted.
#
# Stage 2 assembles and zips on a plain Debian so the executable bits survive,
# and zips without -y so symlinks are dereferenced - Python's zipfile, which
# the in-app updater uses to unpack this archive, writes symlinks as text.

# ---------------------------------------------------------------- stage 1
# The release is x86-64 only; pinning the platform keeps an ARM host from
# silently producing an ARM binary under an x64 name.
FROM --platform=linux/amd64 python:3.12-slim-bullseye AS builder

# bullseye-security's live pool no longer serves the .deb versions its own index
# advertises (mesa 404s), which breaks apt outright. The image already ships the
# matching snapshot.debian.org lines commented out: switch to those, which are
# immutable and complete, and make the build reproducible into the bargain.
RUN sed -i \
        -e 's|^deb http://deb.debian.org|# deb http://deb.debian.org|' \
        -e 's|^# deb http://snapshot.debian.org|deb http://snapshot.debian.org|' \
        /etc/apt/sources.list \
    && printf 'Acquire::Check-Valid-Until "false";\n' > /etc/apt/apt.conf.d/99no-check-valid \
    && printf 'Acquire::Retries "5";\n' > /etc/apt/apt.conf.d/99retries

RUN apt-get update && apt-get install -y --no-install-recommends \
        binutils \
        libgl1 libegl1 libglib2.0-0 libfontconfig1 libdbus-1-3 \
        libxkbcommon0 libxkbcommon-x11-0 libxrender1 \
        libx11-xcb1 libxcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
        libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
        libxcb-shm0 libxcb-sync1 libxcb-util1 libxcb-xfixes0 \
        libxcb-xinerama0 libxcb-xkb1 \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "pyinstaller==6.22.2"

COPY src ./src
COPY CrossPatch-linux.spec .
RUN pyinstaller CrossPatch-linux.spec --noconfirm --distpath /build/out --workpath /build/work

# The failure this guards against is silent, so fail loudly here instead.
RUN test -f /build/out/CrossPatch/_internal/PySide6/Qt/plugins/platforms/libqxcb.so \
    || (echo "FATAL: no xcb platform plugin was collected" && exit 1)

# --- assemble the release tree ---
COPY assets ./assets
COPY tools ./tools
COPY linux ./linux
COPY LICENSE PRIVACY.md README.md version.txt ./

RUN set -eux; \
    stage=/build/stage/CrossPatch; \
    mkdir -p "$stage"; \
    cp -a /build/out/CrossPatch/. "$stage/"; \
    cp -a assets "$stage/assets"; \
    mkdir -p "$stage/tools"; \
    cp -a tools/CrossPatchParser "$stage/tools/CrossPatchParser"; \
    cp -a LICENSE PRIVACY.md README.md "$stage/"; \
    cp -a linux/README-LINUX.md "$stage/"; \
    cp -a linux/run.sh linux/install.sh linux/uninstall.sh "$stage/"; \
    chmod +x "$stage/CrossPatch" "$stage/tools/CrossPatchParser" \
             "$stage/run.sh" "$stage/install.sh" "$stage/uninstall.sh"

# xvfb-run refuses to start without xauth, and says so only at run time.
RUN apt-get update && apt-get install -y --no-install-recommends xauth \
    && rm -rf /var/lib/apt/lists/*

# Smoke test: a window that comes up and stays up is killed by timeout (124).
# Anything else - a missing plugin, an import error - exits earlier with its own
# code, which is the signal we want.
RUN set -eux; \
    cd /build/stage/CrossPatch; \
    ( timeout 25 xvfb-run -a ./CrossPatch > /tmp/smoke.log 2>&1; echo $? > /tmp/smoke.rc ) || true; \
    rc=$(cat /tmp/smoke.rc); \
    echo "--- smoke test output (exit $rc) ---"; cat /tmp/smoke.log || true; \
    test "$rc" = "124" || (echo "FATAL: app did not stay running (exit $rc)" && exit 1)

# ---------------------------------------------------------------- stage 2
FROM --platform=linux/amd64 debian:bullseye-slim AS packager
# Same stale-pool problem as stage 1; the sed is a no-op if the lines differ.
RUN sed -i \
        -e 's|^deb http://deb.debian.org|# deb http://deb.debian.org|' \
        -e 's|^# deb http://snapshot.debian.org|deb http://snapshot.debian.org|' \
        /etc/apt/sources.list \
    && printf 'Acquire::Check-Valid-Until "false";\n' > /etc/apt/apt.conf.d/99no-check-valid \
    && apt-get update && apt-get install -y --no-install-recommends zip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /pkg
COPY --from=builder /build/stage/ ./
COPY --from=builder /build/version.txt .
# No -y: symlinks are stored as the files they point at.
RUN set -eux; \
    v=$(cat version.txt | tr -d '[:space:]'); \
    rm -f version.txt; \
    mkdir -p /out; \
    zip -q -r -9 "/out/CrossPatch-$v-linux-x64.zip" CrossPatch; \
    ls -la /out

# ---------------------------------------------------------------- output
FROM scratch AS export
COPY --from=packager /out/ /
