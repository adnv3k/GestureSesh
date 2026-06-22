"""Reusable dialog components for GestureSesh."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

# Registers the JPEG XL codec with Pillow so .jxl previews can be decoded.
try:
    import pillow_jxl  # noqa: F401
except ImportError:
    pass

from gesturesesh.app.selection_order import (
    BREAK_IMAGE_PATH,
    duplicate_indices,
    selection_stats,
)
from gesturesesh.session.constants import is_hidden_file
from gesturesesh.utils.file_reveal import reveal_in_file_manager


class OrderListWidget(QtWidgets.QListWidget):
    """List widget that reports drag reorders back to its dialog."""

    def dropEvent(self, event):
        super().dropEvent(event)
        dialog = self.window()
        if hasattr(dialog, "_sync_working_files_from_list"):
            dialog._sync_working_files_from_list()


class ImageManagerDialog(QtWidgets.QDialog):
    """Dialog that allows users to inspect, order, and curate selected images."""

    def __init__(
        self,
        parent,
        files,
        duplicate_indices_fn=None,
        on_no_duplicates=None,
        notice_text=None,
        valid_file_types=None,
        folders=None,
        schedule=None,
        locked_until=-1,
        current_index=None,
        validate_files=None,
        title="Selection Order",
        random_preview=False,
    ):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(title)
        self.resize(1100, 680)
        self.setModal(True)

        self._duplicate_indices_fn = duplicate_indices_fn or duplicate_indices
        self._on_no_duplicates = on_no_duplicates
        self._notice_text = notice_text
        self._valid_file_types = {ext.lower() for ext in (valid_file_types or [])}
        self._schedule = schedule or []
        self._locked_until = int(locked_until)
        self._current_index = current_index
        self._validate_files = validate_files
        self.random_preview = bool(random_preview)
        self.working_files = list(files)
        self.working_folders = list(folders or [])
        self._thumbnail_cache = {}
        self._pending_thumbnail_rows = []
        self._pending_thumbnail_keys = set()
        self._thumbnail_generation = 0
        self._placeholder_icon = self._build_placeholder_icon()
        self._thumbnail_timer = QtCore.QTimer(self)
        self._thumbnail_timer.setSingleShot(False)
        self._thumbnail_timer.timeout.connect(self._load_next_thumbnail_batch)

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

        if self.random_preview:
            self.random_label = QtWidgets.QLabel(
                "Randomized preview. Apply will lock this order and turn randomization off.",
                self,
            )
            self.random_label.setWordWrap(True)
            self.random_label.setStyleSheet(
                "background: rgb(32, 57, 68); color: rgb(184, 232, 245);"
                " border: 1px solid rgb(78, 137, 153); border-radius: 4px;"
                " padding: 8px;"
            )
            root_layout.addWidget(self.random_label)

        self.search_input = QtWidgets.QLineEdit(self)
        self.search_input.setPlaceholderText("Filter by filename or path...")
        root_layout.addWidget(self.search_input)

        content_layout = QtWidgets.QHBoxLayout()
        self.images_list = OrderListWidget(self)
        self.images_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.images_list.setAlternatingRowColors(True)
        self.images_list.setIconSize(QtCore.QSize(72, 72))
        self.images_list.setUniformItemSizes(True)
        self.images_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.images_list.setDefaultDropAction(QtCore.Qt.MoveAction)
        content_layout.addWidget(self.images_list, stretch=2)

        details = QtWidgets.QVBoxLayout()
        self.preview_label = QtWidgets.QLabel(self)
        self.preview_label.setMinimumSize(QtCore.QSize(280, 280))
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "background: rgb(18, 32, 43); border: 1px solid rgb(77, 105, 121);"
        )
        self.preview_label.setText("No image selected")
        details.addWidget(self.preview_label)

        self.details_label = QtWidgets.QLabel(self)
        self.details_label.setWordWrap(True)
        self.details_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard
        )
        details.addWidget(self.details_label)
        details.addStretch(1)
        content_layout.addLayout(details, stretch=1)
        root_layout.addLayout(content_layout, stretch=1)

        self.info_label = QtWidgets.QLabel(self)
        root_layout.addWidget(self.info_label)

        controls = QtWidgets.QHBoxLayout()
        self.add_files_btn = QtWidgets.QPushButton("Add Files", self)
        self.add_folder_btn = QtWidgets.QPushButton("Add Folder", self)
        self.remove_selected_btn = QtWidgets.QPushButton("Remove Selected", self)
        self.remove_missing_btn = QtWidgets.QPushButton("Remove Missing", self)
        self.show_duplicates_btn = QtWidgets.QPushButton("Show Duplicates", self)
        self.show_duplicates_btn.setCheckable(True)
        self.move_up_btn = QtWidgets.QPushButton("Move Up", self)
        self.move_down_btn = QtWidgets.QPushButton("Move Down", self)
        self.move_top_btn = QtWidgets.QPushButton("Move Top", self)
        self.move_bottom_btn = QtWidgets.QPushButton("Move Bottom", self)
        self.shuffle_btn = QtWidgets.QPushButton("Shuffle", self)
        self.sort_name_btn = QtWidgets.QPushButton("Sort Name", self)
        self.sort_path_btn = QtWidgets.QPushButton("Sort Path", self)
        self.open_folder_btn = QtWidgets.QPushButton("Open Folder", self)
        self.open_folder_btn.setToolTip(
            "Reveal the highlighted image in your file browser, selecting it."
        )
        self.clear_all_btn = QtWidgets.QPushButton("Clear All", self)

        for widget in (
            self.add_files_btn,
            self.add_folder_btn,
            self.remove_selected_btn,
            self.remove_missing_btn,
            self.show_duplicates_btn,
            self.move_up_btn,
            self.move_down_btn,
            self.move_top_btn,
            self.move_bottom_btn,
            self.shuffle_btn,
            self.sort_name_btn,
            self.sort_path_btn,
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
        self.add_files_btn.clicked.connect(self._add_files)
        self.add_folder_btn.clicked.connect(self._add_folder)
        self.remove_selected_btn.clicked.connect(self._remove_selected)
        self.remove_missing_btn.clicked.connect(self._remove_missing)
        self.show_duplicates_btn.toggled.connect(self._toggle_show_duplicates)
        self.move_up_btn.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_btn.clicked.connect(lambda: self._move_selected(1))
        self.move_top_btn.clicked.connect(lambda: self._move_to_edge(-1))
        self.move_bottom_btn.clicked.connect(lambda: self._move_to_edge(1))
        self.shuffle_btn.clicked.connect(self._shuffle_unlocked)
        self.sort_name_btn.clicked.connect(lambda: self._sort_unlocked("name"))
        self.sort_path_btn.clicked.connect(lambda: self._sort_unlocked("path"))
        self.open_folder_btn.clicked.connect(self._open_selected_folder)
        self.clear_all_btn.clicked.connect(self._clear_all)
        self.search_input.textChanged.connect(self._refresh_list)
        self.images_list.currentItemChanged.connect(self._update_preview)
        self.images_list.verticalScrollBar().valueChanged.connect(
            self._queue_visible_thumbnails
        )
        self.images_list.verticalScrollBar().rangeChanged.connect(
            lambda _minimum, _maximum: self._queue_visible_thumbnails()
        )

        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)

    def accept(self):
        if self._validate_files:
            message = self._validate_files(self.working_files)
            if message:
                QtWidgets.QMessageBox.warning(self, "Cannot Apply Order", message)
                return
        super().accept()

    def _is_locked_index(self, index):
        if index < 0 or index >= len(self.working_files):
            return True
        return index <= self._locked_until or self.working_files[index] == BREAK_IMAGE_PATH

    def _build_placeholder_icon(self):
        pixmap = QtGui.QPixmap(72, 72)
        pixmap.fill(QtGui.QColor("#253847"))
        painter = QtGui.QPainter(pixmap)
        painter.setPen(QtGui.QColor("#8fb5c4"))
        painter.drawRect(10, 12, 52, 48)
        painter.drawLine(16, 50, 30, 36)
        painter.drawLine(30, 36, 42, 48)
        painter.drawLine(42, 48, 56, 30)
        painter.end()
        return QtGui.QIcon(pixmap)

    def _scaled_pixmap_for_path(self, file_path, target_size):
        if file_path == BREAK_IMAGE_PATH or not os.path.exists(file_path):
            return QtGui.QPixmap()

        reader = QtGui.QImageReader(file_path)
        reader.setAutoTransform(True)
        source_size = reader.size()
        if source_size.isValid() and not source_size.isEmpty():
            scaled_size = source_size.scaled(
                target_size, QtCore.Qt.KeepAspectRatio
            )
            reader.setScaledSize(scaled_size)

        image = reader.read()
        if image.isNull():
            # Qt has no plugin for formats like AVIF/JXL; fall back to Pillow.
            image = self._read_image_with_pillow(file_path)
        if image is None or image.isNull():
            return QtGui.QPixmap()
        pixmap = QtGui.QPixmap.fromImage(image)
        if pixmap.isNull():
            return QtGui.QPixmap()
        if pixmap.width() > target_size.width() or pixmap.height() > target_size.height():
            pixmap = pixmap.scaled(
                target_size,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
        return pixmap

    def _read_image_with_pillow(self, file_path):
        if Image is None:
            return None
        try:
            with Image.open(file_path) as pil_image:
                if ImageOps is not None:
                    pil_image = ImageOps.exif_transpose(pil_image)
                pil_image = pil_image.convert("RGBA")
                width, height = pil_image.size
                data = pil_image.tobytes("raw", "RGBA")
            image = QtGui.QImage(
                data, width, height, QtGui.QImage.Format_RGBA8888
            )
            return image.copy()
        except Exception:
            return None

    def _thumbnail_for_path(self, file_path):
        if file_path in self._thumbnail_cache:
            return self._thumbnail_cache[file_path]
        return self._placeholder_icon

    def _queue_thumbnail(self, row, file_path):
        if (
            file_path == BREAK_IMAGE_PATH
            or file_path in self._thumbnail_cache
            or not os.path.exists(file_path)
        ):
            return
        key = (self._thumbnail_generation, row, file_path)
        if key in self._pending_thumbnail_keys:
            return
        self._pending_thumbnail_keys.add(key)
        self._pending_thumbnail_rows.append(key)

    def _start_thumbnail_loading(self):
        if self._pending_thumbnail_rows:
            self._thumbnail_timer.start(15)
        else:
            self._thumbnail_timer.stop()

    def _visible_row_range(self):
        count = self.images_list.count()
        if count <= 0:
            return None

        viewport = self.images_list.viewport()
        top_index = self.images_list.indexAt(QtCore.QPoint(0, 0))
        bottom_index = self.images_list.indexAt(
            QtCore.QPoint(0, max(0, viewport.height() - 1))
        )

        first = top_index.row() if top_index.isValid() else 0
        if bottom_index.isValid():
            last = bottom_index.row()
        else:
            row_height = max(1, self.images_list.sizeHintForRow(first))
            visible_rows = max(12, viewport.height() // row_height + 1)
            last = first + visible_rows

        buffer_rows = 10
        first = max(0, first - buffer_rows)
        last = min(count - 1, last + buffer_rows)
        return first, last

    def _queue_visible_thumbnails(self):
        row_range = self._visible_row_range()
        if row_range is None:
            return
        first, last = row_range
        for row in range(first, last + 1):
            item = self.images_list.item(row)
            if item is None:
                continue
            self._queue_thumbnail(row, item.data(QtCore.Qt.UserRole + 1))
        self._start_thumbnail_loading()

    def _load_next_thumbnail_batch(self):
        batch_size = 2
        target_size = QtCore.QSize(72, 72)
        loaded = 0
        while self._pending_thumbnail_rows and loaded < batch_size:
            generation, row, file_path = self._pending_thumbnail_rows.pop(0)
            self._pending_thumbnail_keys.discard((generation, row, file_path))
            if generation != self._thumbnail_generation:
                continue
            pixmap = self._scaled_pixmap_for_path(file_path, target_size)
            if pixmap.isNull():
                continue
            icon = QtGui.QIcon(pixmap)
            self._thumbnail_cache[file_path] = icon
            if row < self.images_list.count():
                item = self.images_list.item(row)
                if item and item.data(QtCore.Qt.UserRole + 1) == file_path:
                    item.setIcon(icon)
            loaded += 1
        if not self._pending_thumbnail_rows:
            self._thumbnail_timer.stop()

    def _sync_working_files_from_list(self):
        if self.search_input.text().strip():
            self._refresh_list()
            return
        ordered = []
        for row in range(self.images_list.count()):
            item = self.images_list.item(row)
            ordered.append(item.data(QtCore.Qt.UserRole + 1))
        if len(ordered) == len(self.working_files):
            self.working_files = ordered
        self._refresh_list()

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
                self.images_list.setCurrentItem(item)

    def _refresh_list(self):
        self._thumbnail_timer.stop()
        self._pending_thumbnail_rows = []
        self._pending_thumbnail_keys = set()
        self._thumbnail_generation += 1
        query = self.search_input.text().strip().lower()
        self.images_list.clear()
        has_locked_rows = any(
            self._is_locked_index(index) for index in range(len(self.working_files))
        )
        self.images_list.setDragDropMode(
            QtWidgets.QAbstractItemView.NoDragDrop
            if query or has_locked_rows
            else QtWidgets.QAbstractItemView.InternalMove
        )
        visible = 0

        duplicate_indices = self._duplicate_indices_fn(self.working_files)
        show_duplicates = self.show_duplicates_btn.isChecked()
        scheduled_count = selection_stats(
            self.working_files, self.working_folders, self._schedule
        ).scheduled_images
        real_seen = 0

        for index, file_path in enumerate(self.working_files):
            path_lower = file_path.lower()
            base_lower = os.path.basename(file_path).lower()
            if query and query not in path_lower and query not in base_lower:
                continue

            is_break = file_path == BREAK_IMAGE_PATH
            is_duplicate = index in duplicate_indices
            is_locked = self._is_locked_index(index)
            is_current = self._current_index == index
            if not is_break:
                real_seen += 1

            markers = []
            if is_break:
                markers.append("BREAK")
            elif scheduled_count and real_seen <= scheduled_count:
                markers.append("SCHEDULED")
            if is_current:
                markers.append("CURRENT")
            if is_locked:
                markers.append("LOCKED")
            if show_duplicates and is_duplicate:
                markers.append("DUPLICATE")
            if file_path != BREAK_IMAGE_PATH and not os.path.exists(file_path):
                markers.append("MISSING")

            display_name = "Break" if is_break else os.path.basename(file_path)
            marker_text = f"  |  {' / '.join(markers)}" if markers else ""
            item_text = f"{index + 1:03d}. {display_name}{marker_text}\n{file_path}"

            item = QtWidgets.QListWidgetItem(self._thumbnail_for_path(file_path), item_text)
            item.setData(QtCore.Qt.UserRole, index)
            item.setData(QtCore.Qt.UserRole + 1, file_path)

            if is_locked:
                item.setForeground(QtGui.QBrush(QtGui.QColor("#b8c4cc")))
            if file_path != BREAK_IMAGE_PATH and not os.path.exists(file_path):
                item.setForeground(QtGui.QBrush(QtGui.QColor("#ff7f7f")))
            elif show_duplicates and is_duplicate:
                item.setBackground(QtGui.QBrush(QtGui.QColor("#40361e")))
                item.setForeground(QtGui.QBrush(QtGui.QColor("#f5d47a")))
            elif is_current:
                item.setBackground(QtGui.QBrush(QtGui.QColor("#1d4a55")))

            self.images_list.addItem(item)
            visible += 1

        stats = selection_stats(self.working_files, self.working_folders, self._schedule)
        ext_bits = ", ".join(f"{ext}:{count}" for ext, count in stats.extension_counts.items())
        schedule_bits = (
            f"  |  Scheduled: {stats.scheduled_images}"
            f"  |  Extra: {stats.extra_images}"
            f"  |  Short: {stats.shortage_images}"
            if stats.scheduled_images
            else ""
        )
        self.info_label.setText(
            f"Visible: {visible}  |  Total: {stats.total_files}"
            f"  |  Folders: {stats.folder_count}"
            f"{schedule_bits}"
            f"  |  Missing: {stats.missing_files}"
            f"  |  Duplicates: {stats.duplicate_files}"
            f"  |  Types: {ext_bits or 'none'}"
        )
        self._update_preview(self.images_list.currentItem(), None)
        QtCore.QTimer.singleShot(0, self._queue_visible_thumbnails)

    def _update_preview(self, current, previous=None):
        if current is None:
            self.preview_label.setPixmap(QtGui.QPixmap())
            self.preview_label.setText("No image selected")
            self.details_label.setText("")
            return

        index = current.data(QtCore.Qt.UserRole)
        file_path = current.data(QtCore.Qt.UserRole + 1)
        if file_path == BREAK_IMAGE_PATH:
            self.preview_label.setPixmap(QtGui.QPixmap())
            self.preview_label.setText("Break")
            self.details_label.setText(f"Order: {index + 1}\nInternal break marker")
            return

        target_size = self.preview_label.size()
        if not target_size.isValid() or target_size.isEmpty():
            target_size = QtCore.QSize(280, 280)
        pixmap = self._scaled_pixmap_for_path(file_path, target_size)
        if pixmap.isNull():
            self.preview_label.setPixmap(QtGui.QPixmap())
            self.preview_label.setText("Preview unavailable")
            dimensions = "unknown"
        else:
            self.preview_label.setText("")
            self.preview_label.setPixmap(
                pixmap.scaled(
                    target_size,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
            )
            dimensions = f"{pixmap.width()} x {pixmap.height()}"

        size_text = "missing"
        try:
            size_text = f"{Path(file_path).stat().st_size / 1024:.1f} KB"
        except OSError:
            pass
        self.details_label.setText(
            f"Order: {index + 1}\n"
            f"Name: {os.path.basename(file_path)}\n"
            f"Dimensions: {dimensions}\n"
            f"Size: {size_text}\n"
            f"Path: {file_path}"
        )

    def _check_files(self, files):
        valid = []
        for file_path in files:
            # Skip hidden dotfiles / macOS AppleDouble sidecars (._name.ext);
            # they share a real image's extension but aren't decodable images.
            if is_hidden_file(file_path):
                continue
            ext = os.path.splitext(file_path)[1].lower()
            if self._valid_file_types and ext not in self._valid_file_types:
                continue
            if os.path.isfile(file_path):
                valid.append(file_path)
        return valid

    def _add_files(self):
        selected, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Add Images")
        valid = self._check_files(selected)
        if valid:
            self.working_files.extend(valid)
            self._refresh_list()

    def _add_folder(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Add Folder")
        if not directory:
            return
        if directory not in self.working_folders:
            self.working_folders.append(directory)
        added = []
        for root, _dirs, files in os.walk(directory):
            added.extend(self._check_files([os.path.join(root, name) for name in files]))
        self.working_files.extend(added)
        self._refresh_list()

    def _remove_selected(self):
        indices = self._selected_indices()
        if not indices:
            return
        for index in reversed(indices):
            if 0 <= index < len(self.working_files) and not self._is_locked_index(index):
                self.working_files.pop(index)
        self._refresh_list()

    def _remove_missing(self):
        self.working_files = [
            path
            for index, path in enumerate(self.working_files)
            if self._is_locked_index(index) or path == BREAK_IMAGE_PATH or os.path.exists(path)
        ]
        self._refresh_list()

    def _move_selected(self, direction):
        indices = self._selected_indices()
        if not indices:
            return

        if direction < 0:
            for index in indices:
                if (
                    index <= 0
                    or index - 1 in indices
                    or self._is_locked_index(index)
                    or self._is_locked_index(index - 1)
                ):
                    continue
                self.working_files[index - 1], self.working_files[index] = (
                    self.working_files[index],
                    self.working_files[index - 1],
                )
            new_indices = [max(0, i - 1) for i in indices]
        else:
            for index in reversed(indices):
                if (
                    index >= len(self.working_files) - 1
                    or index + 1 in indices
                    or self._is_locked_index(index)
                    or self._is_locked_index(index + 1)
                ):
                    continue
                self.working_files[index + 1], self.working_files[index] = (
                    self.working_files[index],
                    self.working_files[index + 1],
                )
            new_indices = [min(len(self.working_files) - 1, i + 1) for i in indices]

        self._refresh_list()
        self._reselect_indices(new_indices)

    def _move_to_edge(self, direction):
        previous = None
        while previous != self.working_files:
            previous = list(self.working_files)
            self._move_selected(direction)

    def _unlocked_indices(self):
        return [
            index
            for index in range(len(self.working_files))
            if not self._is_locked_index(index)
        ]

    def _replace_unlocked(self, ordered_paths):
        unlocked = self._unlocked_indices()
        for index, path in zip(unlocked, ordered_paths):
            self.working_files[index] = path
        self._refresh_list()

    def _shuffle_unlocked(self):
        import random

        paths = [self.working_files[index] for index in self._unlocked_indices()]
        random.shuffle(paths)
        self._replace_unlocked(paths)

    def _sort_unlocked(self, mode):
        paths = [self.working_files[index] for index in self._unlocked_indices()]
        if mode == "name":
            paths.sort(key=lambda path: os.path.basename(path).lower())
        else:
            paths.sort(key=lambda path: path.lower())
        self._replace_unlocked(paths)

    def _open_selected_folder(self):
        indices = self._selected_indices()
        if not indices:
            return

        target = self.working_files[indices[0]]
        if target and target != BREAK_IMAGE_PATH:
            # Reveal-and-select the highlighted image so it's easy to spot,
            # mirroring the session window's "open folder" behavior.
            reveal_in_file_manager(target)

    def _clear_all(self):
        self.working_files = [
            path for index, path in enumerate(self.working_files) if self._is_locked_index(index)
        ]
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
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowTitle("Shortcut Map")
        self.resize(620, 460)
        self._shortcut_rows = shortcut_rows
        self._top_items = []

        self._setup_ui()
        self._populate_rows()
        # Allow F1 to close the dialog as a toggle (mirrors session hotkey)
        try:
            close_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("F1"), self)
            close_shortcut.activated.connect(self.accept)
        except Exception:
            pass

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
        self.tree.setStyleSheet(
            "QTreeWidget {"
            " background-color: rgb(24, 43, 59);"
            " alternate-background-color: rgb(33, 57, 76);"
            " color: rgb(236, 242, 247); }"
            "QTreeWidget::item { padding: 3px 4px; }"
            "QTreeWidget::item:selected {"
            " background-color: rgb(68, 201, 176); color: rgb(12, 24, 33); }"
            "QHeaderView::section {"
            " background-color: rgb(30, 56, 78); color: rgb(236, 242, 247);"
            " padding: 4px; border: 0px; }"
        )
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
            parent.setForeground(0, QtGui.QBrush(QtGui.QColor(125, 214, 240)))
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
    duplicate_indices_fn=None,
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


def run_selection_order_dialog(parent, files, **kwargs):
    """Open selection order viewer and return updated files/folders when accepted."""
    dialog = ImageManagerDialog(parent=parent, files=files, **kwargs)
    if dialog.exec() != QtWidgets.QDialog.Accepted:
        return None
    return {
        "files": dialog.working_files,
        "folders": dialog.working_folders,
        "random_preview": dialog.random_preview,
    }


def run_shortcut_map_dialog(parent, shortcut_rows):
    """Open shortcut-map dialog."""
    dialog = ShortcutMapDialog(parent=parent, shortcut_rows=shortcut_rows)
    dialog.exec()
