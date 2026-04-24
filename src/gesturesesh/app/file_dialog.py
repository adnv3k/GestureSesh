"""File dialog widgets used by the main window."""

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QListView,
    QTreeView,
)


class FileDialog(QFileDialog):
    """QFileDialog subclass that supports selecting multiple folders."""

    def __init__(self):
        super(FileDialog, self).__init__()
        self.setOption(QFileDialog.DontUseNativeDialog, True)
        self.setFileMode(QFileDialog.Directory)
        self.setOption(QFileDialog.ShowDirsOnly, True)
        self.findChildren(QListView)[0].setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.findChildren(QTreeView)[0].setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
