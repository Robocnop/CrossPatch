"""First-run screen: checks the setup and explains the basics in one place.

New users otherwise meet CrossPatch through two folder pickers and an empty
list, with nothing saying what Save & Apply does or that GameBanana's
1-Click button works with it.
"""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QFileDialog, QGridLayout
)
from PySide6.QtCore import Qt

from Localization import tr


def game_folder_looks_valid(path):
    return bool(path) and os.path.isdir(os.path.join(path, "UNION"))


def ue4ss_installed(game_root):
    if not game_root:
        return False
    win64 = os.path.join(game_root, "UNION", "Binaries", "Win64")
    return os.path.isdir(os.path.join(win64, "ue4ss")) and os.path.exists(os.path.join(win64, "dwmapi.dll"))


class WelcomeDialog(QDialog):
    def __init__(self, parent, cfg, parser_ok):
        super().__init__(parent)
        self.cfg = cfg
        self.parser_ok = parser_ok
        self.game_root_changed = False
        self.setWindowTitle(tr("welcome.title"))
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        heading = QLabel(f"<h2>{tr('welcome.heading')}</h2>")
        layout.addWidget(heading)

        checks = QFrame()
        checks.setFrameShape(QFrame.StyledPanel)
        self.grid = QGridLayout(checks)
        layout.addWidget(checks)

        self.change_game_btn = QPushButton(tr("welcome.change_game"))
        self.change_game_btn.clicked.connect(self._change_game_root)
        self._fill_checks()

        tips = QLabel(tr("welcome.tips"))
        tips.setWordWrap(True)
        tips.setTextFormat(Qt.RichText)
        layout.addWidget(tips)

        buttons = QHBoxLayout()
        buttons.addStretch()
        start_btn = QPushButton(tr("welcome.start"))
        start_btn.setDefault(True)
        start_btn.clicked.connect(self.accept)
        buttons.addWidget(start_btn)
        layout.addLayout(buttons)

    def _row(self, row, ok, label, detail):
        mark = QLabel("✅" if ok else "⚠️")
        self.grid.addWidget(mark, row, 0)
        self.grid.addWidget(QLabel(f"<b>{label}</b>"), row, 1)
        detail_label = QLabel(detail)
        detail_label.setWordWrap(True)
        detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.grid.addWidget(detail_label, row, 2)

    def _fill_checks(self):
        while self.grid.count():
            widget = self.grid.takeAt(0).widget()
            if widget and widget is not self.change_game_btn:
                widget.deleteLater()

        game_root = self.cfg.get("game_root", "")
        game_ok = game_folder_looks_valid(game_root)
        self._row(0, game_ok, tr("welcome.check.game"),
                  game_root if game_ok else tr("welcome.check.game_bad", path=game_root or "?"))
        self.grid.addWidget(self.change_game_btn, 0, 3)

        mods_folder = self.cfg.get("mods_folder", "")
        self._row(1, os.path.isdir(mods_folder), tr("welcome.check.mods"), mods_folder)

        has_ue4ss = ue4ss_installed(game_root)
        self._row(2, has_ue4ss, tr("welcome.check.ue4ss"),
                  tr("welcome.check.ue4ss_ok") if has_ue4ss else tr("welcome.check.ue4ss_missing"))

        self._row(3, self.parser_ok, tr("welcome.check.parser"),
                  tr("welcome.check.parser_ok") if self.parser_ok else tr("welcome.check.parser_missing"))

    def _change_game_root(self):
        folder = QFileDialog.getExistingDirectory(self, tr("setup.game.pick"), self.cfg.get("game_root", ""))
        if folder:
            self.cfg["game_root"] = folder
            self.game_root_changed = True
            self._fill_checks()
