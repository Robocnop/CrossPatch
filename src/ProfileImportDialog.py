"""Reviewing and running the import of a shared profile.

`ProfileImportDialog` shows what the file asks for before anything is
downloaded, and `ProfileImportRunner` then fetches the missing mods one at a
time. Downloads are chained rather than run in parallel because
`DownloadManager` owns a modal progress dialog, and because GameBanana does
not appreciate a dozen simultaneous requests from the same install.
"""

import os
import threading

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTreeWidget,
    QTreeWidgetItem, QDialogButtonBox, QHeaderView, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QColor

import Util
import ProfileSharing
from DownloadManager import DownloadManager
from FileSelectDialog import FileSelectDialog
from Localization import tr


class ProfileImportDialog(QDialog):
    """Lets the user name the incoming profile and see what it will install."""

    def __init__(self, parent, payload, entries, taken_names):
        super().__init__(parent)

        self.entries = entries
        self.taken_names = {name.lower() for name in taken_names}

        self.setWindowTitle(tr("profile.import.window.title"))
        self.resize(720, 460)

        layout = QVBoxLayout(self)

        header = QLabel(tr("profile.import.header",
                           name=payload.get("profile_name", ""),
                           count=len(entries)))
        header.setWordWrap(True)
        layout.addWidget(header)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(tr("profile.import.name")))
        self.name_edit = QLineEdit(self._suggest_name(payload.get("profile_name") or "Imported"))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels([
            tr("profile.import.col.mod"),
            tr("profile.import.col.author"),
            tr("profile.import.col.version"),
            tr("profile.import.col.status"),
        ])
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QAbstractItemView.NoSelection)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tree)

        for entry in entries:
            item = QTreeWidgetItem([
                entry["name"],
                entry["author"] or tr("common.na"),
                entry["version"] or tr("common.na"),
                self._status_text(entry["status"]),
            ])
            if entry["status"] == ProfileSharing.STATUS_UNAVAILABLE:
                # There is no page to download it from, so it cannot be part of
                # the profile. Saying so beats leaving a checkbox that does
                # nothing.
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable & ~Qt.ItemIsEnabled)
                item.setCheckState(0, Qt.Unchecked)
                item.setToolTip(3, tr("profile.import.status.unavailable.tip"))
                item.setForeground(3, QColor("indianred"))
            else:
                item.setCheckState(0, Qt.Checked)
            self.tree.addTopLevelItem(item)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.addButton(tr("profile.import.button"), QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _suggest_name(self, base):
        """Keeps the exported name unless a local profile already uses it."""
        if base.lower() not in self.taken_names:
            return base
        index = 2
        while f"{base} ({index})".lower() in self.taken_names:
            index += 1
        return f"{base} ({index})"

    @staticmethod
    def _status_text(status):
        if status == ProfileSharing.STATUS_INSTALLED:
            return tr("profile.import.status.installed")
        if status == ProfileSharing.STATUS_DOWNLOAD:
            return tr("profile.import.status.download")
        return tr("profile.import.status.unavailable")

    def _on_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, tr("common.error"), tr("profile.import.name_empty"))
            return
        if name.lower() in self.taken_names:
            QMessageBox.warning(self, tr("common.error"), tr("profile.import.name_taken", name=name))
            return

        for index, entry in enumerate(self.entries):
            item = self.tree.topLevelItem(index)
            entry["skipped"] = item.checkState(0) != Qt.Checked

        if all(entry["skipped"] for entry in self.entries):
            QMessageBox.warning(self, tr("common.error"), tr("profile.import.nothing"))
            return

        self.profile_name = name
        self.accept()

    def get_profile_name(self):
        return getattr(self, "profile_name", "")


class ProfileImportRunner(QObject):
    """Downloads the mods an imported profile is missing, one after another."""

    progress = Signal(str)
    finished = Signal(object)

    # Carries the GameBanana lookup back from its worker thread.
    _resolved = Signal(object, object, str)

    def __init__(self, window, entries, mods_folder):
        super().__init__(window)
        self.window = window
        self.entries = entries
        self.mods_folder = mods_folder
        self._queue = []
        self._current = None
        self._manager = None
        self._done = 0
        self._total = 0
        self._resolved.connect(self._on_resolved)

    def start(self):
        self._queue = [e for e in self.entries
                       if e["status"] == ProfileSharing.STATUS_DOWNLOAD and not e["skipped"]]
        self._total = len(self._queue)
        self._done = 0
        self._step()

    def _step(self):
        if not self._queue:
            self.finished.emit(self.entries)
            return

        self._current = self._queue.pop(0)
        self.progress.emit(tr("profile.import.progress",
                              name=self._current["name"],
                              done=self._done + 1,
                              total=self._total))
        threading.Thread(target=self._resolve_worker, args=(self._current,), daemon=True).start()

    def _resolve_worker(self, entry):
        """Asks GameBanana for the submission behind the recorded page URL."""
        try:
            item_data = Util.get_gb_item_data_from_url(entry["mod_page"])
            self._resolved.emit(entry, item_data, "")
        except Exception as e:
            self._resolved.emit(entry, None, str(e))

    def _on_resolved(self, entry, item_data, error):
        if error or not item_data:
            self._abandon(entry, error or tr("profile.import.error.no_data"))
            return

        file_info = ProfileSharing.pick_file(entry, item_data)
        if file_info is None:
            if not item_data.get("_aFiles"):
                self._abandon(entry, tr("profile.import.error.no_files"))
                return
            # Several archives and nothing that identifies the right one, so
            # the user picks rather than CrossPatch installing the wrong
            # variant of the mod.
            dialog = FileSelectDialog(self.window, item_data)
            if not dialog.exec():
                self._abandon(entry, tr("profile.import.error.cancelled"))
                return
            file_info = dialog.get_selection()
            if not file_info:
                self._abandon(entry, tr("profile.import.error.cancelled"))
                return

        self._manager = DownloadManager(self.window, self.mods_folder,
                                        on_complete=self._on_download_complete,
                                        refresh_browse=False)
        # DownloadManager already reports the failure to the user; this second
        # connection is how the summary at the end knows about it.
        self._manager.signals.error.connect(self._on_download_error)
        self._manager.download_specific_file(file_info, item_data,
                                             folder_name=entry["local_folder"])

    def _on_download_error(self, message):
        if self._current:
            self._current["error"] = message

    def _on_download_complete(self):
        entry = self._current
        if entry:
            installed = os.path.isdir(os.path.join(self.mods_folder, entry["local_folder"]))
            if entry["error"] or not installed:
                entry["skipped"] = True
                if not entry["error"]:
                    entry["error"] = tr("profile.import.error.not_extracted")
            self._done += 1
        self._current = None
        self._manager = None
        self._step()

    def _abandon(self, entry, message):
        entry["skipped"] = True
        entry["error"] = message
        self._done += 1
        self._current = None
        self._step()
