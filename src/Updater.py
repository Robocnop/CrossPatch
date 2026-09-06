import os
import sys
import platform
import shutil
import shlex
import subprocess
import tempfile
import threading
import time
import requests

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QMessageBox
from PySide6.QtCore import Signal, QObject, Qt

from Constants import APP_VERSION 
from Config import is_packaged
from Localization import tr
import Util

class UpdaterSignals(QObject):
    """Defines signals for communicating from the worker thread to the GUI."""
    progress = Signal(int)
    label_text = Signal(str)
    finished = Signal()
    error = Signal(str)
    request_download = Signal(str, str) # url, file_path

class ProgressDialog(QDialog):
    """A simple dialog to show update progress."""
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(350)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        self.label = QLabel(tr("updater.initializing"))
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_label(self, text):
        self.label.setText(text)

class Updater:
    def __init__(self, parent, remote_version_info):
        self.parent = parent
        self.remote_version_info = remote_version_info
        self.temp_dir = os.path.join(os.path.dirname(sys.executable) if is_packaged() else os.path.dirname(__file__), 'update_temp')
        self.signals = UpdaterSignals()
        self.progress_dialog = None

        self.signals.finished.connect(self._on_finish)
        self.signals.error.connect(self._on_error)
        self.signals.request_download.connect(self._start_download)

    def start_update(self):
        """Starts the update process in a new thread."""
        # Show the dialog immediately and start a thread to find the asset URL.
        self.progress_dialog = ProgressDialog(self.parent, tr("updater.title"))
        self.signals.progress.connect(self.progress_dialog.update_progress)
        self.signals.label_text.connect(self.progress_dialog.update_label)
        threading.Thread(target=self._find_asset_and_request_download, daemon=True).start()
        self.progress_dialog.exec()

    def _start_download(self, url, file_path):
        threading.Thread(target=self._download_and_install_thread, args=(url, file_path), daemon=True).start()

    def _on_finish(self):
        if self.progress_dialog:
            self.progress_dialog.accept()
        self.parent.close()

    def _on_error(self, error_message):
        if self.progress_dialog:
            self.progress_dialog.reject()
        QMessageBox.critical(self.parent, tr("updater.failed.title"), tr("updater.failed.body", error=error_message))
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _find_asset_and_request_download(self):
        try:
            self.signals.label_text.emit(tr("updater.finding_asset"))
            asset = self._find_release_asset()
            if not asset:
                raise ValueError(tr("updater.no_asset"))

            download_url = asset['browser_download_url']
            archive_path = os.path.join(self.temp_dir, asset['name'])
            os.makedirs(self.temp_dir, exist_ok=True)

            self.signals.request_download.emit(download_url, archive_path)
        except Exception as e:
            self.signals.error.emit(str(e))

    def _download_and_install_thread(self, url, archive_path):
        try:
            self.signals.label_text.emit(tr("updater.downloading", name=os.path.basename(archive_path)))
            self._download_file_with_progress(url, archive_path)

            extract_path = os.path.join(self.temp_dir, 'extracted')
            self._extract_archive(archive_path, extract_path, self.signals.label_text)

            self.signals.label_text.emit(tr("updater.finalizing"))
            self._run_updater_script(extract_path)
            self.signals.finished.emit()

        except Exception as e:
            self.signals.error.emit(str(e))

    def _find_release_asset(self):
        is_windows = platform.system() == "Windows"
        available_assets = self.remote_version_info.get('assets', [])
        if not available_assets:
            return None

        for asset in available_assets:
            asset_name = asset.get('name', '').lower()
            if not asset_name.endswith('.zip'):
                continue
            is_linux_asset = 'linux' in asset_name
            if (is_windows and not is_linux_asset) or (not is_windows and is_linux_asset):
                return asset
        return None

    def _download_file_with_progress(self, url, destination_path):
        with requests.get(url, stream=True, headers={'User-Agent': f'CrossPatch-Updater/{APP_VERSION}'}) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            bytes_downloaded = 0
            with open(destination_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    if total_size > 0:
                        progress = (bytes_downloaded / total_size) * 100
                        self.signals.progress.emit(int(progress))
            self.signals.progress.emit(100)

    def _run_updater_script(self, source_path):
        app_path = os.path.dirname(sys.executable) if is_packaged() else os.path.dirname(os.path.abspath(__file__))
        app_executable = os.path.basename(sys.executable)
        app_exe_path = os.path.join(app_path, app_executable)
        pid = os.getpid()

        # The script lives outside update_temp so it can delete that folder while
        # still running, and so it survives if the app directory is read-only.
        script_dir = tempfile.mkdtemp(prefix='crosspatch-update-')

        if platform.system() == "Windows":
            script_path = os.path.join(script_dir, 'updater.bat')
            # Ensure all paths are double-quoted to handle spaces correctly.
            script_content = f"""@echo off
title CrossPatch Updater
echo Waiting for CrossPatch (PID: {pid}) to close...
set /a WAITED=0
:waitloop
tasklist /fi "PID eq {pid}" /nh 2>nul | find "{pid}" >nul
if errorlevel 1 goto closed
set /a WAITED+=1
if %WAITED% geq 15 goto forcekill
timeout /t 1 /nobreak >nul
goto waitloop

:forcekill
echo CrossPatch did not exit on its own, closing it now...
taskkill /f /pid {pid} >nul 2>&1
timeout /t 2 /nobreak >nul

:closed
echo.
echo Updating files in "{app_path}"...
xcopy "{source_path}" "{app_path}" /E /Y /I /Q
if errorlevel 1 goto failed

echo Cleaning up...
rmdir /s /q "{self.temp_dir}"

echo Update successful! Restarting CrossPatch...
start "" "{app_exe_path}"
(goto) 2>nul & rmdir /s /q "{script_dir}"
exit /b 0

:failed
echo.
echo UPDATE FAILED while copying the new files into "{app_path}".
echo Your installation may be incomplete - please reinstall CrossPatch manually
echo from https://github.com/Robocnop/CrossPatch/releases
echo.
pause
exit /b 1
"""
            with open(script_path, 'w') as f:
                f.write(script_content)
            subprocess.Popen(f'start "" "{script_path}"', creationflags=subprocess.DETACHED_PROCESS, shell=True)
            time.sleep(1)

        else: # Linux
            script_path = os.path.join(script_dir, 'updater.sh')
            script_content = f"""#!/bin/bash
PID={pid}
APP_DIR={shlex.quote(app_path)}
APP_EXE={shlex.quote(app_exe_path)}
SRC_DIR={shlex.quote(source_path)}
TEMP_DIR={shlex.quote(self.temp_dir)}
SCRIPT_DIR={shlex.quote(script_dir)}

echo "Waiting for CrossPatch (PID: $PID) to close..."
WAITED=0
while kill -0 "$PID" 2>/dev/null; do
    sleep 1
    WAITED=$((WAITED + 1))
    if [ "$WAITED" -ge 15 ]; then
        echo "CrossPatch did not exit on its own, closing it now..."
        kill -9 "$PID" 2>/dev/null
        sleep 2
        break
    fi
done

echo "Updating files in $APP_DIR..."
# Trailing '/.' copies the contents, dotfiles included, without nesting them.
if ! cp -a "$SRC_DIR/." "$APP_DIR/"; then
    echo ""
    echo "UPDATE FAILED while copying the new files into $APP_DIR."
    echo "Your installation may be incomplete - please reinstall CrossPatch"
    echo "manually from https://github.com/Robocnop/CrossPatch/releases"
    echo ""
    read -r -p "Press Enter to close..."
    exit 1
fi

chmod +x "$APP_EXE"

echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo "Relaunching CrossPatch..."
nohup "$APP_EXE" >/dev/null 2>&1 &

# Detached, so this script's own directory is removed after it has exited.
nohup bash -c 'sleep 2; rm -rf "$1"' _ "$SCRIPT_DIR" >/dev/null 2>&1 &
"""
            with open(script_path, 'w') as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)
            subprocess.Popen([script_path], start_new_session=True)
            time.sleep(1)

    def _extract_archive(self, archive_path, dest_path, progress_signal=None, clean_destination=True, finished_signal=None):
        """
        Extracts a release archive to a destination path.

        Delegates to Util.extract_archive, which flattens the single top-level
        folder that the release zips wrap everything in. This used to be a local
        copy of that function, but the copy had lost the flattening step, so the
        updater scripts were handed '<extracted>/CrossPatch/...' instead of
        '<extracted>/...' and every update silently landed in the wrong place.
        """
        if progress_signal:
            progress_signal.emit(tr("updater.extracting"))
        Util.extract_archive(
            archive_path,
            dest_path,
            progress_signal=None,  # already emitted above, translated
            clean_destination=clean_destination,
            finished_signal=finished_signal,
        )

        if not os.listdir(dest_path):
            raise RuntimeError(f"The downloaded archive '{os.path.basename(archive_path)}' extracted to nothing.")
