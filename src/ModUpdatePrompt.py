from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialogButtonBox
)
from PySide6.QtCore import Qt
from Localization import tr

class ModUpdatePromptWindow(QDialog):
    def __init__(self, parent, mod_name, current_version, new_version):
        super().__init__(parent)

        self.setWindowTitle(tr("modupdateprompt.title"))
        self.setModal(True)

        layout = QVBoxLayout(self)

        message = tr("modupdateprompt.body", name=mod_name, current=current_version, new=new_version)
        layout.addWidget(QLabel(message))

        button_box = QDialogButtonBox()
        update_button = button_box.addButton(tr("common.update"), QDialogButtonBox.AcceptRole)
        ignore_button = button_box.addButton(tr("common.ignore"), QDialogButtonBox.RejectRole)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setAttribute(Qt.WA_DeleteOnClose)