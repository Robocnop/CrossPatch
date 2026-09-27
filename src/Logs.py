"""Session log file.

Everything the app prints also goes to <CONFIG_DIR>/logs/crosspatch.log. The
packaged Windows build has no console, so until now a user reporting a bug
had nothing to send unless they had turned the console on beforehand and
reproduced the problem.

Each start rotates the previous logs (crosspatch.log -> crosspatch.1.log...),
so the log of a session that crashed is still there after restarting.
"""

import datetime
import os
import sys
import threading

KEEP_SESSIONS = 3
LOG_NAME = "crosspatch.log"

_log_dir = None
_log_path = None


class _Tee:
    """Writes to the log file and to whichever console stream is attached."""

    def __init__(self, log_file, console):
        self._log = log_file
        self.console = console
        self._lock = threading.Lock()

    def write(self, text):
        with self._lock:
            try:
                self._log.write(text)
                self._log.flush()
            except Exception:
                # The log is a convenience; it must never break a print().
                pass
            if self.console is not None:
                try:
                    self.console.write(text)
                except Exception:
                    pass
        return len(text)

    def flush(self):
        if self.console is not None:
            try:
                self.console.flush()
            except Exception:
                pass

    def isatty(self):
        return False


def _rotate(directory):
    oldest = os.path.join(directory, f"crosspatch.{KEEP_SESSIONS - 1}.log")
    if os.path.exists(oldest):
        os.remove(oldest)
    for index in range(KEEP_SESSIONS - 2, 0, -1):
        src = os.path.join(directory, f"crosspatch.{index}.log")
        if os.path.exists(src):
            os.replace(src, os.path.join(directory, f"crosspatch.{index + 1}.log"))
    current = os.path.join(directory, LOG_NAME)
    if os.path.exists(current):
        os.replace(current, os.path.join(directory, "crosspatch.1.log"))


def install(config_dir, app_version):
    """Starts mirroring stdout and stderr into the log file."""
    global _log_dir, _log_path
    if isinstance(sys.stdout, _Tee):
        return _log_path

    _log_dir = os.path.join(config_dir, "logs")
    try:
        os.makedirs(_log_dir, exist_ok=True)
        _rotate(_log_dir)
        _log_path = os.path.join(_log_dir, LOG_NAME)
        log_file = open(_log_path, "w", encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"Could not open the log file: {e}")
        return None

    log_file.write(f"CrossPatch {app_version}, session started "
                   f"{datetime.datetime.now().isoformat(timespec='seconds')}\n")
    # A windowed build has no stdout at all (None): the tee then only logs.
    sys.stdout = _Tee(log_file, sys.stdout)
    sys.stderr = _Tee(log_file, sys.stderr)
    return _log_path


def attach_console(out, err):
    """Routes console output to new streams, keeping the log going.

    Returns False when logging is not installed and the caller should swap
    sys.stdout itself.
    """
    if isinstance(sys.stdout, _Tee) and isinstance(sys.stderr, _Tee):
        sys.stdout.console = out
        sys.stderr.console = err
        return True
    return False


def log_dir():
    return _log_dir


def log_path():
    return _log_path
