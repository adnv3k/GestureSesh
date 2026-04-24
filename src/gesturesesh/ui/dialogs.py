"""Reusable dialog components for GestureSesh."""

from __future__ import annotations

import os

from PyQt5 import QtCore, QtGui, QtWidgets


class ImageManagerDialog(QtWidgets.QDialog):
    """Dialog that allows users to inspect and curate currently loaded images."""

    def __init__(
        self,
        parent,
        files,
        duplicate_indices_fn,
        on_no_duplicates=None,
        notice_text=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Manage Loaded Images")
        self.resize(940, 560)
        self.setModal(True)

        self._duplicate_indices_fn = duplicate_indices_fn
        self._on_no_duplicates = on_no_duplicates
        self._notice_text = notice_text
        self.working_files = list(files)

        self._setup_ui()
        self._connect_signals()
        self._refresh_list()

    def _setup_ui(self):
        root_layout = QtWidgets.QVBoxLayout(self)

        if self._notice_text:
            self.notice_label = QtWidgets.QLabel(self._notice_text, self)
            self.notice_label.setWordWrap(True)
            self.notice_label.setStyleSheet(
                "background: rgb(61, 52, 24); color: rgb(244, 223, 138);"
                " border: 1px solid rgb(128, 104, 36); border-radius: 4px;"
                " padding: 8px;"
            )
            root_layout.addWidget(self.notice_label)

        self.search_input = QtWidgets.QLineEdit(self)
        self.search_input.setPlaceholderText("Filter by filename or path...")
        root_layout.addWidget(self.search_input)

        self.images_list = QtWidgets.QListWidget(self)
        self.images_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.images_list.setAlternatingRowColors(True)
        root_layout.addWidget(self.images_list, stretch=1)

        self.info_label = QtWidgets.QLabel(self)
        root_layout.addWidget(self.info_label)

        controls = QtWidgets.QHBoxLayout()
        self.remove_selected_btn = QtWidgets.QPushButton("Remove Selected", self)
        self.remove_missing_btn = QtWidgets.QPushButton("Remove Missing", self)
        self.show_duplicates_btn = QtWidgets.QPushButton("Show Duplicates", self)
        self.show_duplicates_btn.setCheckable(True)
        self.move_up_btn = QtWidgets.QPushButton("Move Up", self)
        self.move_down_btn = QtWidgets.QPushButton("Move Down", self)
        self.open_folder_btn = QtWidgets.QPushButton("Open Folder", self)
        self.clear_all_btn = QtWidgets.QPushButton("Clear All", self)

        for widget in (
            self.remove_selected_btn,
            self.remove_missing_btn,
            self.show_duplicates_btn,
            self.move_up_btn,
            self.move_down_btn,
            self.open_folder_btn,
            self.clear_all_btn,
        ):
            controls.addWidget(widget)
        root_layout.addLayout(controls)

        self.dialog_buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok,
            parent=self,
        )
        self.dialog_buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("Apply")
        root_layout.addWidget(self.dialog_buttons)

    def _connect_signals(self):
        self.remove_selected_btn.clicked.connect(self._remove_selected)
        self.remove_missing_btn.clicked.connect(self._remove_missing)
        self.show_duplicates_btn.toggled.connect(self._toggle_show_duplicates)
        self.move_up_btn.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_btn.clicked.connect(lambda: self._move_selected(1))
        self.open_folder_btn.clicked.connect(self._open_selected_folder)
        self.clear_all_btn.clicked.connect(self._clear_all)
        self.search_input.textChanged.connect(self._refresh_list)

        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)

    def _selected_indices(self):
        return sorted(
            {
                item.data(QtCore.Qt.UserRole)
                for item in self.images_list.selectedItems()
                if item.data(QtCore.Qt.UserRole) is not None
            }
        )

    def _reselect_indices(self, indices):
        keep = set(indices)
        for row in range(self.images_list.count()):
            item = self.images_list.item(row)
            if item.data(QtCore.Qt.UserRole) in keep:
                item.setSelected(True)

    def _refresh_list(self):
        query = self.search_input.text().strip().lower()
        self.images_list.clear()
        visible = 0
        missing = 0

        duplicate_indices = self._duplicate_indices_fn(self.working_files)
        show_duplicates = self.show_duplicates_btn.isChecked()

        for index, file_path in enumerate(self.working_files):
            path_lower = file_path.lower()
            base_lower = os.path.basename(file_path).lower()
            if query and query not in path_lower and query not in base_lower:
                continue

            item_text = file_path
            is_duplicate = index in duplicate_indices
            if show_duplicates and is_duplicate:
                item_text = f"{item_text}  |  DUPLICATE"

            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, index)

            if not os.path.exists(file_path):
                missing += 1
                item.setForeground(QtGui.QBrush(QtGui.QColor("#ff7f7f")))
            elif show_duplicates and is_duplicate:
                item.setBackground(QtGui.QBrush(QtGui.QColor("#40361e")))
                item.setForeground(QtGui.QBrush(QtGui.QColor("#f5d47a")))

            self.images_list.addItem(item)
            visible += 1

        duplicates_total = len(duplicate_indices)
        self.info_label.setText(
            f"Visible: {visible}  |  Total: {len(self.working_files)}  |  Missing: {missing}"
            f"  |  Duplicates: {duplicates_total}"
        )

    def _remove_selected(self):
        indices = self._selected_indices()
        if not indices:
            return
        for index in reversed(indices):
            if 0 <= index < len(self.working_files):
                self.working_files.pop(index)
        self._refresh_list()

    def _remove_missing(self):
        self.working_files = [path for path in self.working_files if os.path.exists(path)]
        self._refresh_list()

    def _move_selected(self, direction):
        indices = self._selected_indices()
        if not indices:
            return

        if direction < 0:
            for index in indices:
                if index <= 0 or index - 1 in indices:
                    continue
                self.working_files[index - 1], self.working_files[index] = (
                    self.working_files[index],
                    self.working_files[index - 1],
                )
            new_indices = [max(0, i - 1) for i in indices]
        else:
            for index in reversed(indices):
                if index >= len(self.working_files) - 1 or index + 1 in indices:
                    continue
                self.working_files[index + 1], self.working_files[index] = (
                    self.working_files[index],
                    self.working_files[index + 1],
                )
            new_indices = [min(len(self.working_files) - 1, i + 1) for i in indices]

        self._refresh_list()
        self._reselect_indices(new_indices)

    def _open_selected_folder(self):
        indices = self._selected_indices()
        if not indices:
            return

        target = self.working_files[indices[0]]
        folder = os.path.dirname(target)
        if folder and os.path.isdir(folder):
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl.fromLocalFile(os.path.abspath(folder))
            )

    def _clear_all(self):
        self.working_files.clear()
        self._refresh_list()

    def _toggle_show_duplicates(self, checked):
        if checked:
            self.show_duplicates_btn.setText("Hide Duplicates")
            if self._on_no_duplicates and not self._duplicate_indices_fn(self.working_files):
                self._on_no_duplicates()
        else:
            self.show_duplicates_btn.setText("Show Duplicates")
        self._refresh_list()


class ShortcutMapDialog(QtWidgets.QDialog):
    """Dialog that displays the available keyboard and input shortcuts."""

    def __init__(self, parent, shortcut_rows):
        super().__init__(parent)
        self.setWindowTitle("Shortcut Map")
        self.resize(620, 460)
        self._shortcut_rows = shortcut_rows
        self._top_items = []

        self._setup_ui()
        self._populate_rows()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        description = QtWidgets.QLabel(
            "Hover an action name for details. Use these shortcuts while the session window is focused.",
            self,
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: rgb(210, 226, 236);")
        layout.addWidget(description)

        self.search_input = QtWidgets.QLineEdit(self)
        self.search_input.setPlaceholderText("Search shortcuts or actions...")
        self.search_input.textChanged.connect(self._filter_rows)
        layout.addWidget(self.search_input)

        self.tree = QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Shortcut", "Action"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.tree)

        close_button = QtWidgets.QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignRight)

    def _populate_rows(self):
        grouped_rows = {}
        seen = set()
        for group, shortcut, action, details in self._shortcut_rows:
            key = (group, shortcut, action)
            if key in seen:
                continue
            seen.add(key)
            grouped_rows.setdefault(group, []).append((shortcut, action, details))

        for group in sorted(grouped_rows.keys()):
            parent = QtWidgets.QTreeWidgetItem([group, ""])
            parent.setFirstColumnSpanned(True)
            parent.setFlags(parent.flags() & ~QtCore.Qt.ItemIsSelectable)
            parent.setForeground(0, QtGui.QBrush(QtGui.QColor(140, 199, 216)))
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)

            for shortcut, action, details in sorted(
                grouped_rows[group], key=lambda row: row[0].lower()
            ):
                child = QtWidgets.QTreeWidgetItem([shortcut, action])
                child.setToolTip(1, details)
                child.setData(0, QtCore.Qt.UserRole, details)
                parent.addChild(child)

            self.tree.addTopLevelItem(parent)
            parent.setExpanded(True)
            self._top_items.append(parent)

    def _filter_rows(self, query):
        query = query.strip().lower()
        for group_item in self._top_items:
            visible_children = 0
            for idx in range(group_item.childCount()):
                child = group_item.child(idx)
                shortcut_text = child.text(0).lower()
                action_text = child.text(1).lower()
                details = str(child.data(0, QtCore.Qt.UserRole)).lower()
                matches = (
                    not query
                    or query in shortcut_text
                    or query in action_text
                    or query in details
                    or query in group_item.text(0).lower()
                )
                child.setHidden(not matches)
                if matches:
                    visible_children += 1
            group_item.setHidden(visible_children == 0)


def run_image_manager_dialog(
    parent,
    files,
    duplicate_indices_fn,
    on_no_duplicates=None,
    notice_text=None,
):
    """Open image manager and return the updated list when accepted."""
    dialog = ImageManagerDialog(
        parent=parent,
        files=files,
        duplicate_indices_fn=duplicate_indices_fn,
        on_no_duplicates=on_no_duplicates,
        notice_text=notice_text,
    )
    if dialog.exec() != QtWidgets.QDialog.Accepted:
        return None
    return dialog.working_files


def run_shortcut_map_dialog(parent, shortcut_rows):
    """Open shortcut-map dialog."""
    dialog = ShortcutMapDialog(parent=parent, shortcut_rows=shortcut_rows)
    dialog.exec()
