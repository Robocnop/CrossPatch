"""Shared test setup.

Config.CONFIG_DIR is decided at import time, so portable mode and a scratch
working directory are set up here, before any test module imports the app.
Without this the tests would read and write the real %APPDATA%\\CrossPatch.
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")

_scratch = tempfile.mkdtemp(prefix="crosspatch-tests-")
os.environ["CROSSPATCH_PORTABLE"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.chdir(_scratch)

if SRC not in sys.path:
    sys.path.insert(0, SRC)
