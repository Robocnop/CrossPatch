"""Overview of every file conflict between the enabled mods of a profile.

The conflict dialog shown while applying mods only reports problems; this one
explains them in terms of load order and lets the user settle each one by
choosing which mod loads last.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from Localization import tr

_ROLE_MOD = Qt.UserRole
_ROLE_GROUP = Qt.UserRole + 1


class ConflictOverviewDialog(QDialog):
    """Lists conflict groups; `on_load_last(mod, others)` returns new groups."""

    def __init__(self, parent, groups, display_names, on_load_last):
        super().__init__(parent)
        self.setWindowTitle(tr("conflicts.overview.title"))
        self.resize(820, 560)
        self.display_names = display_names
        self.on_load_last = on_load_last
        self.changed = False

        layout = QVBoxLayout(self)
        intro = QLabel(tr("conflicts.overview.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels([tr("conflicts.overview.col.item"), tr("conflicts.overview.col.detail")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.currentItemChanged.connect(self._on_selection)
        layout.addWidget(self.tree)

        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        buttons = QHBoxLayout()
        self.load_last_btn = QPushButton(tr("conflicts.overview.load_last"))
        self.load_last_btn.setEnabled(False)
        self.load_last_btn.clicked.connect(self._load_selected_last)
        buttons.addWidget(self.load_last_btn)
        buttons.addStretch()
        close_btn = QPushButton(tr("common.close"))
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self._populate(groups)

    def _name(self, mod):
        return self.display_names.get(mod, mod)

    def _populate(self, groups):
        self.tree.clear()
        if not groups:
            self.tree.addTopLevelItem(QTreeWidgetItem([tr("conflicts.overview.none"), ""]))
            self.load_last_btn.setEnabled(False)
            return

        bold = QFont()
        bold.setBold(True)
        for group in groups:
            mods = group["mods"]
            title = " / ".join(self._name(m) for m in mods)
            top = QTreeWidgetItem([title, tr("conflicts.overview.files", count=len(group["files"]))])
            top.setFont(0, bold)
            self.tree.addTopLevelItem(top)

            for position, mod in enumerate(mods, start=1):
                is_last = position == len(mods)
                detail = tr("conflicts.overview.likely_wins") if is_last else ""
                row = QTreeWidgetItem([tr("conflicts.overview.position", position=position, name=self._name(mod)), detail])
                row.setData(0, _ROLE_MOD, mod)
                row.setData(0, _ROLE_GROUP, mods)
                if is_last:
                    row.setForeground(1, QColor("springgreen"))
                top.addChild(row)

            files_item = QTreeWidgetItem([tr("conflicts.overview.file_list"), ""])
            for path in group["files"]:
                files_item.addChild(QTreeWidgetItem([path, ""]))
            top.addChild(files_item)
            top.setExpanded(True)

    def _on_selection(self, current, _previous):
        mod = current.data(0, _ROLE_MOD) if current else None
        mods = current.data(0, _ROLE_GROUP) if current else None
        can_move = bool(mod) and bool(mods) and mods[-1] != mod
        self.load_last_btn.setEnabled(can_move)

    def _load_selected_last(self):
        item = self.tree.currentItem()
        if not item:
            return
        mod = item.data(0, _ROLE_MOD)
        others = [m for m in (item.data(0, _ROLE_GROUP) or []) if m != mod]
        if not mod or not others:
            return
        groups = self.on_load_last(mod, others)
        self.changed = True
        self.hint.setText(tr("conflicts.overview.apply_hint"))
        self._populate(groups)
