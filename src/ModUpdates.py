"""Updating every outdated mod in one go.

Same shape as ProfileImportRunner: one mod at a time, because DownloadManager
owns a modal progress dialog and GameBanana does not like bursts of requests.

The right archive is picked the way a profile import does it: the file the
mod was installed from, else the one carrying the new version. Only when that
stays ambiguous is the user asked.
"""

import os
import threading

from PySide6.QtCore import QObject, Signal

import Util
import ProfileSharing
from DownloadManager import DownloadManager
from FileSelectDialog import FileSelectDialog
from Localization import tr


class UpdateAllRunner(QObject):
    progress = Signal(str)
    # [(display name, error message or "")]
    finished = Signal(object)

    _resolved = Signal(object, object, str)

    def __init__(self, window, updates, mods_folder, active_profile):
        super().__init__(window)
        self.window = window
        self.mods_folder = mods_folder
        self.active_profile = active_profile
        self._queue = list(updates.values())
        self._total = len(self._queue)
        self._results = []
        self._current = None
        self._error = ""
        self._manager = None
        self._resolved.connect(self._on_resolved)

    def start(self):
        self._step()

    def _step(self):
        if not self._queue:
            self.finished.emit(self._results)
            return
        self._current = self._queue.pop(0)
        self._error = ""
        self.progress.emit(tr("modupdate.all.progress", name=self._current["name"],
                              done=len(self._results) + 1, total=self._total))
        threading.Thread(target=self._resolve_worker, args=(self._current,), daemon=True).start()

    def _resolve_worker(self, update):
        try:
            self._resolved.emit(update, Util.get_gb_item_data_from_url(update["url"]), "")
        except Exception as e:
            self._resolved.emit(update, None, str(e))

    def _on_resolved(self, update, item_data, error):
        if error or not item_data:
            self._finish_one(error or tr("profile.import.error.no_data"))
            return

        info = Util.read_mod_info(os.path.join(self.mods_folder, update["folder_name"]))
        wanted = {"source_file": info.get("source_file", ""), "version": update.get("new", "")}
        file_info = ProfileSharing.pick_file(wanted, item_data)
        if file_info is None:
            if not item_data.get("_aFiles"):
                self._finish_one(tr("profile.import.error.no_files"))
                return
            dialog = FileSelectDialog(self.window, item_data)
            file_info = dialog.get_selection() if dialog.exec() else None
            if not file_info:
                self._finish_one(tr("profile.import.error.cancelled"))
                return

        self._manager = DownloadManager(self.window, self.mods_folder,
                                        on_complete=self._on_download_complete,
                                        refresh_browse=False)
        self._manager.signals.error.connect(self._on_download_error)
        self._manager.update_specific_file(file_info, item_data, update["folder_name"], self.active_profile)

    def _on_download_error(self, message):
        self._error = message

    def _on_download_complete(self):
        self._manager = None
        self._finish_one(self._error)

    def _finish_one(self, error):
        self._results.append((self._current["name"], error or ""))
        self._current = None
        self._step()
