import sys
import webbrowser

from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from Constants import APP_VERSION, SOURCE_URL, UPSTREAM_URL, LICENSE_URL
from Localization import tr


class CreditsWindow(QDialog):
    """Credits, and the notices GPL-3.0 requires from a modified version.

    Section 5(a) of the GPL asks a modified work to carry prominent notices
    saying it was changed; section 4 asks us to keep the original copyright
    and authorship intact. Both live here, next to the source link that
    makes the licence actually usable by whoever receives the program.
    """

    MAINTAINERS = [
        ("Robocnop", "credits.role.maintainer"),
    ]

    ORIGINAL_TEAM = [
        ("NockCS", "credits.role.lead"),
        ("RED1", "credits.role.secondary"),
        ("AntiApple4life", "credits.role.linux"),
        ("Ben Thalmann", "credits.role.cleanup"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(tr("credits.title"))
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        title = QLabel(tr("credits.version", version=APP_VERSION))
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(10)

        self._add_section(layout, tr("credits.maintained_by"), self.MAINTAINERS)
        layout.addSpacing(10)
        self._add_section(layout, tr("credits.original_team"), self.ORIGINAL_TEAM)
        layout.addSpacing(10)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        licence = QLabel(tr("credits.licence"))
        licence.setWordWrap(True)
        licence_font = QFont()
        licence_font.setPointSize(9)
        licence.setFont(licence_font)
        layout.addWidget(licence)
        layout.addSpacing(10)

        button_row = QHBoxLayout()
        source_btn = QPushButton(tr("credits.source_btn"))
        source_btn.clicked.connect(lambda: self._open(SOURCE_URL))
        button_row.addWidget(source_btn)

        upstream_btn = QPushButton(tr("credits.upstream_btn"))
        upstream_btn.clicked.connect(lambda: self._open(UPSTREAM_URL))
        button_row.addWidget(upstream_btn)

        licence_btn = QPushButton(tr("credits.licence_btn"))
        licence_btn.clicked.connect(lambda: self._open(LICENSE_URL))
        button_row.addWidget(licence_btn)
        layout.addLayout(button_row)

        close_button = QPushButton(tr("common.close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def _add_section(self, layout, heading, people):
        heading_label = QLabel(heading)
        heading_font = QFont()
        heading_font.setPointSize(9)
        heading_font.setBold(True)
        heading_label.setFont(heading_font)
        heading_label.setStyleSheet("color: #8fb8de;")
        layout.addWidget(heading_label)

        for name, role_key in people:
            name_label = QLabel(name)
            name_font = QFont()
            name_font.setPointSize(12)
            name_font.setBold(True)
            name_label.setFont(name_font)
            layout.addWidget(name_label)

            role_label = QLabel(tr(role_key))
            role_font = QFont()
            role_font.setPointSize(9)
            role_label.setFont(role_font)
            layout.addWidget(role_label)

    def _open(self, url):
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Could not open {url}: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CreditsWindow()
    window.show()
    sys.exit(app.exec())
