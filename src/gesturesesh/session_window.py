"""Session display runtime for GestureSesh."""

from __future__ import annotations

import math
import os
import platform
import random
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path

import cv2
import numpy as np
from pygame import mixer

try:
    from PIL import Image, ImageOps, ImageSequence
except ImportError:
    Image = None
    ImageOps = None
    ImageSequence = None

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QShortcut, QWidget

from gesturesesh.session.constants import (
    BREAK_IMAGE_PATH,
    SUPPORTED_ANIMATED_TYPES,
    SUPPORTED_IMAGE_TYPES,
    sound_file,
)
from gesturesesh.session.image_mods import SessionImageModsMixin
from gesturesesh.session.shortcuts import SessionShortcutsMixin
from gesturesesh.session.timer import SessionTimerMixin
from gesturesesh.session.zoom_pan import SessionZoomPanMixin
from gesturesesh.utils import resources_config  # noqa: F401
from gesturesesh.ui.dialogs import run_shortcut_map_dialog, ShortcutMapDialog
from gesturesesh.ui.dot_indicator import DotIndicator
from gesturesesh.ui.session_display import Ui_session_display


class SessionDisplay(
    SessionImageModsMixin,
    SessionShortcutsMixin,
    SessionTimerMixin,
    SessionZoomPanMixin,
    QWidget,
    Ui_session_display,
):
    closed = QtCore.pyqtSignal()  # Needed here for close event to work.

    def __init__(self, schedule=None, items=None, total=None, parent=None, settings=None):
        super().__init__(parent)
        self.setupUi(self)
        self.init_sizing()

        self.init_scaling_size()
        # Hide the old numeric status label
        self.session_info.hide()

        # Top row → images in current entry | Bottom row → entries in session
        self.image_progress = DotIndicator(
            parent=self, dot_d=11, top_overlay=True
        )  # larger cyan
        self.entry_progress = DotIndicator(
            parent=self, dot_d=8, top_overlay=True
        )  # smaller green
        self.image_progress.setContentsMargins(0, 0, 0, 0)
        self.entry_progress.setContentsMargins(0, 0, 0, 0)

        # Pack the two rows into a left‑hand container so the central control
        # buttons remain perfectly centred.
        self.indicators_container = QWidget()
        vbox = QtWidgets.QVBoxLayout(self.indicators_container)
        vbox.setContentsMargins(0, 0, 1, 0)  # no unwanted vertical gap
        vbox.setSpacing(0)
        # make the thickness of the border thinner
        self.indicators_container.setStyleSheet(
            "QWidget { rgba(85,85,85,0.25); border-radius: 4px; }"
        )
        vbox.addWidget(self.image_progress)
        vbox.addWidget(self.entry_progress)

        # Insert the container at the far‑left edge of the control row
        controls_layout_item: QtWidgets.QLayoutItem = self.verticalLayout.itemAt(1)
        if controls_layout_item and isinstance(
            controls_layout_item.layout(), QtWidgets.QHBoxLayout
        ):
            controls_layout = controls_layout_item.layout()
            controls_layout.insertWidget(0, self.indicators_container, stretch=0)

            # Prevent the container from hogging horizontal space.
            self.indicators_container.setSizePolicy(
                QtWidgets.QSizePolicy.Preferred,
                QtWidgets.QSizePolicy.Fixed,
            )

            # Keep the controls cluster centred when the window is resized.
            self._adjust_progressbar_width()
        self.drag_timer_was_active = False
        self.drag_start_position = QtCore.QPoint()
        self.drag_threshold = 6
        self.schedule = schedule
        self.playlist = items
        self.playlist_position = 0
        self.total_scheduled_images = total
        self.init_timer()
        self.init_animation_state()
        self.init_zoom_pan()
        self.init_session_toggles()
        self.init_button_sizes()
        self.horizontalLayout_2.setAlignment(QtCore.Qt.AlignVCenter)
        self.horizontalLayout.setAlignment(QtCore.Qt.AlignVCenter)
        self.horizontalLayout_3.setAlignment(QtCore.Qt.AlignVCenter)
        self.horizontalLayout_4.setAlignment(QtCore.Qt.AlignVCenter)
        self.init_entries()
        self.installEventFilter(self)
        self.image_display.installEventFilter(self)
        if sys.platform != "darwin":
            self.image_display.grabGesture(QtCore.Qt.PinchGesture)
        self.image_display.setTabletTracking(True)
        pause_style = "background: rgb(100, 120, 118); padding:2px;"
        for btn in (
            self.previous_image,
            self.pause_timer,
            self.stop_session,
            self.next_image,
            self.grayscale_button,
            self.flip_horizontal_button,
            self.flip_vertical_button,
        ):
            btn.setMinimumSize(60, 32)
            btn.setStyleSheet(pause_style)
            self.horizontalLayout.setAlignment(btn, QtCore.Qt.AlignVCenter)
            self.horizontalLayout_2.setAlignment(btn, QtCore.Qt.AlignVCenter)
        self.init_image_mods()
        # Apply persisted session settings after init_image_mods so that
        # image_mods exists when apply_session_settings accesses it.
        if settings:
            try:
                self.apply_session_settings(settings)
            except Exception:
                pass
        self.init_mixer()
        break_indices = [
            i for i, entry in enumerate(self.schedule) if entry.images == 0
        ]
        self.entry_progress.setBreaks(break_indices)
        self.entry_progress.setMaximum(len(self.schedule))
        self.entry_progress.setValue(1)
        self.load_entry()
        self.init_buttons()
        self.init_shortcuts()
        self.skip_count = 0

    def init_session_toggles(self):
        self.zoom_toggle_button = QtWidgets.QPushButton("Zoom", self)
        self.zoom_toggle_button.setCheckable(True)
        self.zoom_toggle_button.setChecked(False)
        self.zoom_toggle_button.setToolTip(
            "Enable zoom and pan controls.\nDefault: Off\nShortcut: Z"
        )
        self.zoom_toggle_button.clicked.connect(self.toggle_zoom_enabled)

        self.shortcuts_button = QtWidgets.QPushButton("?", self)
        self.shortcuts_button.setToolTip("Open shortcut map.\nShortcut: F1")
        self.shortcuts_button.clicked.connect(self.open_shortcut_map)

        for button in (
            self.zoom_toggle_button,
            self.shortcuts_button,
        ):
            button.setFocusPolicy(QtCore.Qt.NoFocus)
            button.setStyleSheet("background: rgb(119, 153, 146);")
            self.horizontalLayout_2.addWidget(button, 0, QtCore.Qt.AlignBottom)

        self.session_info.hide()


    def init_sizing(self):
        """
        Resizes the window to half of the current screen's resolution,
        sets states for window flags,
        and initializes self.previous_size.

        """
        self.resize(self.screen().availableSize() / 2)
        self.setMinimumSize(QtCore.QSize(360, 1))
        self.toggle_resize_status = False
        self.toggle_always_on_top_status = False
        self.frameless_status = False
        self.sizePolicy().setHeightForWidth(True)
        self.previous_size = self.size()

    def init_scaling_size(self):
        """
        Creates a scaling box size that is used as a basis for
        images to scale off of. The box dimensions are determined by the
        smallest side of half of the given rectangle from the
        current screen's available resolution.

        """
        half_screen = self.screen().availableSize() / 2
        min_length = min(half_screen.height(), half_screen.width())
        self.scaling_size = QtCore.QSize(min_length, min_length)

    def init_animation_state(self):
        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.setSingleShot(True)
        self.animation_timer.timeout.connect(self._advance_animation_frame)
        self.animation_frames = []
        self.animation_durations_ms = []
        self.animation_frame_index = 0
        self.animation_source_path = None
        self.max_still_cache_entries = 64
        self.max_animation_cache_entries = 12
        self.still_image_cache = OrderedDict()
        self.animation_cache = OrderedDict()

    def reset_animation_state(self):
        if hasattr(self, "animation_timer"):
            self.animation_timer.stop()
        self.animation_frames = []
        self.animation_durations_ms = []
        self.animation_frame_index = 0
        self.animation_source_path = None

    def clear_decode_caches(self):
        self.still_image_cache.clear()
        self.animation_cache.clear()

    def _cache_get(self, cache, key):
        value = cache.get(key)
        if value is not None:
            cache.move_to_end(key)
        return value

    def _cache_put(self, cache, key, value, limit):
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > limit:
            cache.popitem(last=False)

    def init_entries(self):
        self.entry = {
            "current": 0,
            "total": len(self.schedule),
            "amount of items": self.schedule[0].images,
            "time": self.schedule[0].time,
        }
        self.new_entry = True
        if self.entry["amount of items"] > 1:
            self.end_of_entry = False
        else:
            self.end_of_entry = True
        self._reset_indicator_pulse_markers()
        print(f"self.endofentry: {self.end_of_entry}")

    def _reset_indicator_pulse_markers(self):
        self._last_milestone_stage = 0

    def _session_progress_pulse_count(self):
        total = max(1, int(self.total_scheduled_images or 0))
        if total <= 0:
            return 1
        progress = (self.playlist_position + 1) / total
        if progress < 0.33:
            return 1
        if progress < 0.66:
            return 2
        if progress < 0.9:
            return 3
        return 4

    def _trigger_progress_burst(self, pulse_count):
        pulse_count = max(1, min(4, int(pulse_count)))
        for idx in range(pulse_count):
            QtCore.QTimer.singleShot(
                idx * 220,
                self.entry_progress.trigger_milestone_pulse,
            )

    def _update_predictive_indicator_cues(self):
        if self.session_finished:
            return
        if (
            self.playlist_position >= len(self.playlist)
            or self.playlist[self.playlist_position] == BREAK_IMAGE_PATH
        ):
            return

        total = max(1, int(self.entry["time"]))
        elapsed = max(0, total - int(math.ceil(self.time_seconds)))

        stage = int((elapsed / total) * 4)
        if stage > self._last_milestone_stage and stage in (1, 2, 3):
            self._last_milestone_stage = stage
            self.image_progress.trigger_soft_pulse()
            self._trigger_progress_burst(self._session_progress_pulse_count())

    def init_mixer(self):
        mixer.init()
        try:
            """
            If view.mute exists, then a session has been started before.
            Set mute and volume according to previous session's sound settings.
            """
            import __main__

            if hasattr(__main__, "view") and hasattr(__main__.view, "mute"):
                if __main__.view.mute is True:  # if view.mute exists and is True
                    self.mute = True
                    self.volume = mixer.music.get_volume()
                    mixer.music.set_volume(0.0)
                else:  # if view.mute exists and is False
                    self.mute = False
                    self.volume = __main__.view.volume
            else:
                self.volume = mixer.music.get_volume()
                self.mute = False
        except:  # view.mute does not exist, so init settings with default.
            self.volume = mixer.music.get_volume()
            self.mute = False

    def init_button_sizes(self):
        """Ensure all control buttons use a consistent size on any platform"""
        button_size = QtCore.QSize(70, 40) if sys.platform == "darwin" else QtCore.QSize(60, 36)
        icon_size = QtCore.QSize(28, 28)
        self._icon_buttons = [
            self.previous_image,
            self.pause_timer,
            self.stop_session,
            self.next_image,
            self.grayscale_button,
            self.flip_horizontal_button,
            self.flip_vertical_button,
        ]
        for btn in self._icon_buttons:
            btn.setFixedSize(button_size)
            btn.setIconSize(icon_size)
        self.zoom_toggle_button.setMinimumWidth(54)
        self.zoom_toggle_button.setFixedHeight(button_size.height())
        self.shortcuts_button.setFixedSize(QtCore.QSize(36, button_size.height()))
        self._update_control_density()

    def init_buttons(self):
        self.previous_image.clicked.connect(self.previous_playlist_position)
        self.next_image.clicked.connect(self.load_next_image)
        self.stop_session.clicked.connect(self.close)
        self.flip_horizontal_button.clicked.connect(self.flip_horizontal)
        self.flip_vertical_button.clicked.connect(self.flip_vertical)
        self.grayscale_button.clicked.connect(self.grayscale)
        self.pause_timer.clicked.connect(self.pause)

    def init_shortcuts(self):
        self.shortcut_map_rows = []

        def register_shortcut(sequence, callback, action, details, group):
            shortcut = QShortcut(QtGui.QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self.shortcut_map_rows.append((group, sequence, action, details))
            return shortcut

        # Resize
        self.toggle_resize_key = register_shortcut(
            "R",
            self.toggle_resize,
            "Toggle resize mode",
            "Switch between fit-inside and fill-window display behavior.",
            "Window & View",
        )
        # Always on top
        self.always_on_top_key = register_shortcut(
            "A",
            self.toggle_always_on_top,
            "Toggle always-on-top",
            "Keep the slideshow window above other windows.",
            "Window & View",
        )
        # Mute
        self.mute_key = register_shortcut(
            "M",
            self.toggle_mute,
            "Toggle mute",
            "Mute/unmute session sound cues.",
            "Audio & Timing",
        )
        # Timer
        self.add_30 = register_shortcut(
            "Up",
            self.add_30_seconds,
            "Add 30 seconds",
            "Increase current timer by 30 seconds.",
            "Audio & Timing",
        )
        self.add_60 = register_shortcut(
            "Ctrl+Up",
            self.add_60_seconds,
            "Add 60 seconds",
            "Increase current timer by 60 seconds.",
            "Audio & Timing",
        )
        self.restart = register_shortcut(
            "Ctrl+Shift+Up",
            self.restart_timer,
            "Restart timer",
            "Reset the current image timer to its scheduled duration.",
            "Audio & Timing",
        )
        # Skip image
        self.skip_image_key = register_shortcut(
            "S",
            self.skip_image,
            "Skip image",
            "Swap current image forward with a later image in the session.",
            "Navigation",
        )
        # Frameless Window
        self.frameless_window = register_shortcut(
            "Ctrl+F",
            self.toggle_frameless,
            "Toggle frameless window",
            "Hide/show window frame.",
            "Window & View",
        )
        # Image adjustments
        self.brightness_up = register_shortcut(
            "Ctrl+PgUp",
            self.increase_brightness,
            "Increase brightness",
            "Raise brightness modifier.",
            "Image Filters",
        )
        self.brightness_down = register_shortcut(
            "Ctrl+PgDown",
            self.decrease_brightness,
            "Decrease brightness",
            "Lower brightness modifier.",
            "Image Filters",
        )
        self.contrast_up = register_shortcut(
            "PgUp",
            self.increase_contrast,
            "Increase contrast",
            "Raise contrast modifier.",
            "Image Filters",
        )
        self.contrast_down = register_shortcut(
            "PgDown",
            self.decrease_contrast,
            "Decrease contrast",
            "Lower contrast modifier.",
            "Image Filters",
        )
        self.threshold_toggle = register_shortcut(
            "T",
            self.toggle_threshold,
            "Toggle threshold",
            "Enable/disable threshold filter.",
            "Image Filters",
        )
        self.edge_toggle = register_shortcut(
            "E",
            self.toggle_edge,
            "Toggle edge filter",
            "Enable/disable edge detection filter.",
            "Image Filters",
        )
        self.reset_mods = register_shortcut(
            "Ctrl+0",
            self.reset_image_mods,
            "Reset image modifiers",
            "Reset brightness/contrast/filters/flip for current image.",
            "Image Filters",
        )
        self.toggle_grayscale_mode_shortcut = register_shortcut(
            "Ctrl+G",
            self.toggle_grayscale_mode,
            "Toggle grayscale algorithm",
            "Switch between perceptual and simple grayscale conversion.",
            "Image Filters",
        )
        # Open image directory
        self.open_directory_key = register_shortcut(
            "Ctrl+O",
            self.open_image_directory,
            "Open image folder",
            "Open the folder containing the current image.",
            "Navigation",
        )
        # Zoom controls
        self.zoom_toggle_key = register_shortcut(
            "Z",
            self.toggle_zoom_enabled,
            "Toggle zoom/pan",
            "Enable or disable zoom and pan interaction.",
            "Zoom & Pan",
        )
        self.zoom_reset_key = register_shortcut(
            "0",
            self.reset_zoom_to_default,
            "Reset zoom",
            "Reset zoom back to default 1.0x and center.",
            "Zoom & Pan",
        )
        self.quick_inspect_key = register_shortcut(
            "I",
            self.quick_inspect,
            "Quick inspect toggle",
            "Toggle between default zoom and inspection zoom.",
            "Zoom & Pan",
        )
        self.zoom_autoreset_key = register_shortcut(
            "Ctrl+Shift+Z",
            self.toggle_zoom_reset_mode,
            "Toggle auto zoom reset",
            "Enable/disable resetting zoom when moving to another image.",
            "Zoom & Pan",
        )
        self.shortcut_map_key = register_shortcut(
            "F1",
            self.open_shortcut_map,
            "Open shortcut map",
            "Show all available shortcuts and what they do.",
            "Help",
        )
        self.shortcut_map_key2 = register_shortcut(
            "Ctrl+/",
            self.open_shortcut_map,
            "Open shortcut map",
            "Show all available shortcuts and what they do.",
            "Help",
        )
        self.shortcut_map_rows.extend(
            [
                (
                    "Navigation",
                    "Left / Right",
                    "Previous / next image",
                    "Move backward or forward in the slideshow.",
                ),
                (
                    "Audio & Timing",
                    "Space",
                    "Pause / resume",
                    "Pause or resume the timer while in session.",
                ),
                (
                    "Navigation",
                    "Esc",
                    "Stop session",
                    "Close the session window.",
                ),
                (
                    "Zoom & Pan",
                    "Mouse wheel",
                    "Zoom (when zoom enabled)",
                    "Fast wheel movement gives larger jumps; slow wheel gives finer control.",
                ),
                (
                    "Zoom & Pan",
                    "Two-finger scroll",
                    "Pan (touchpad)",
                    "Pan the zoomed image directly with touchpad scroll.",
                ),
                (
                    "Zoom & Pan",
                    "Stylus drag",
                    "Pan (tablet/pen)",
                    "Drag with a pen when zoomed to pan the canvas.",
                ),
                (
                    "Zoom & Pan",
                    "Ctrl + stylus drag",
                    "Zoom (tablet/pen)",
                    "Adjust zoom by dragging vertically while holding Ctrl.",
                ),
                (
                    "Zoom & Pan",
                    "Pinch gesture",
                    "Zoom (touchpad)",
                    "Pinch-to-zoom is cursor-centered when zoom is enabled.",
                ),
            ]
        )

    def _update_control_density(self):
        if not hasattr(self, "zoom_toggle_button"):
            return
        width = self.width()
        if width <= 500:
            button_size = QtCore.QSize(42, 28)
            icon_size = QtCore.QSize(16, 16)
            text_h = 28
            spacing = 0
        elif width <= 680:
            button_size = QtCore.QSize(50, 32)
            icon_size = QtCore.QSize(20, 20)
            text_h = 32
            spacing = 1
        else:
            button_size = QtCore.QSize(70, 40) if sys.platform == "darwin" else QtCore.QSize(60, 36)
            icon_size = QtCore.QSize(28, 28)
            text_h = button_size.height()
            spacing = 1

        for btn in getattr(self, "_icon_buttons", []):
            btn.setFixedSize(button_size)
            btn.setIconSize(icon_size)

        self.zoom_toggle_button.setFixedHeight(text_h)
        self.zoom_toggle_button.setMinimumWidth(46 if width <= 520 else 54)
        self.shortcuts_button.setFixedSize(QtCore.QSize(30 if width <= 520 else 36, text_h))
        self.timer_display.setFixedHeight(text_h)
        self.horizontalLayout_3.setAlignment(self.timer_display, QtCore.Qt.AlignVCenter)

        # Hide lower-priority controls as width shrinks.
        compact = width <= 760
        ultra_compact = width <= 610
        micro = width <= 500
        self.grayscale_button.setVisible(not compact)
        self.flip_horizontal_button.setVisible(not compact)
        self.flip_vertical_button.setVisible(not compact)
        self.shortcuts_button.setVisible(not ultra_compact)
        self.zoom_toggle_button.setVisible(not micro)

        self.horizontalLayout.setSpacing(spacing)
        self.horizontalLayout_2.setSpacing(spacing)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setSpacing(spacing)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)

    def _pulse_indicators_softly(self):
        self.image_progress.trigger_soft_pulse()
        self.entry_progress.trigger_soft_pulse()

    def open_shortcut_map(self):
        # Toggle a non-modal shortcut-map dialog. If visible, close it.
        try:
            dlg = getattr(self, "_shortcut_map_dialog", None)
            if dlg is not None and dlg.isVisible():
                try:
                    dlg.close()
                except Exception:
                    pass
                self._shortcut_map_dialog = None
                return
            dlg = ShortcutMapDialog(parent=self, shortcut_rows=self.shortcut_map_rows)
            dlg.setModal(False)
            dlg.show()
            dlg.raise_()
            self._shortcut_map_dialog = dlg
        except Exception:
            # fallback to the blocking dialog
            try:
                run_shortcut_map_dialog(parent=self, shortcut_rows=self.shortcut_map_rows)
            except Exception:
                pass

    # --- dynamic centring helpers ------------------------------------------
    # --- SessionDisplay ---------------------------------------------------

    def _adjust_progressbar_width(self):
        """
        Give the indicators_container just enough width for *all* currently
        rendered dots, then set the left/right spacers to equal stretch so
        the control buttons float back to dead-centre.
        """
        try:
            needed = max(
                self.image_progress.sizeHint().width(),
                self.entry_progress.sizeHint().width(),
            )
            self.indicators_container.setFixedWidth(needed + 12)  # +8 px margin

            # Re-centre: both spacer items get stretch=1, everything else = 0
            controls_layout: QtWidgets.QLayout = self.verticalLayout.itemAt(1).layout()
            for i in range(controls_layout.count()):
                item = controls_layout.itemAt(i)
                controls_layout.setStretch(i, 1 if item.spacerItem() else 0)
        except Exception:
            pass

    def _controls_row_height(self):
        try:
            controls_layout_item = self.verticalLayout.itemAt(1)
            if controls_layout_item and controls_layout_item.layout():
                layout = controls_layout_item.layout()
                margins = layout.contentsMargins()
                return max(
                    32,
                    layout.sizeHint().height() + margins.top() + margins.bottom() + 2,
                )
        except Exception:
            pass
        return 40

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_progressbar_width()
        self._update_control_density()
        if (
            getattr(self, "toggle_resize_status", False)
            and hasattr(self, "image")
            and not self.image.isNull()
        ):
            self.image_scaled = self.image.scaled(
                self.image_display.size(),
                aspectRatioMode=QtCore.Qt.KeepAspectRatio,
                transformMode=QtCore.Qt.SmoothTransformation,
            )
        self.update_image_view()

    def closeEvent(self, event):
        """
        Stops timer and sound on close event.
        """
        self.timer.stop()
        self.reset_animation_state()
        self.clear_decode_caches()
        self.close_timer.stop()
        if hasattr(self, "idle_indicator_pulse_timer"):
            self.idle_indicator_pulse_timer.stop()
        # Store session sound settings globally for next session
        try:
            import __main__

            if hasattr(__main__, "view"):
                __main__.view.mute = self.mute
                __main__.view.volume = self.volume
        except:
            pass
        mixer.quit()
        self.closed.emit()
        event.accept()

    def mousePressEvent(self, event):
        """
        Stores the initial cursor position and whether the timer was active
        before any dragging begins.
        """
        self.old_position = event.globalPos()
        self.drag_start_position = event.globalPos()
        # Record if the timer is active at the start of a potential drag
        self.was_timer_active = self.timer.isActive()
        # Reset drag flag
        self.drag_timer_was_active = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Drags the window by the difference between the current cursor position and self.old_position.
        Pauses the timer on the first movement if it was active before dragging.
        """
        # Start a drag only if the cursor moved beyond the threshold
        if (
            event.globalPos() - self.drag_start_position
        ).manhattanLength() > self.drag_threshold:
            if not self.drag_timer_was_active:
                # Only pause timer if session is not finished
                if not self.session_finished and self.timer.isActive():
                    self.timer.stop()
                    self._set_timer_visuals(False)
                self.drag_timer_was_active = True

        if self.drag_timer_was_active:
            change = event.globalPos() - self.old_position
            self.move(self.x() + change.x(), self.y() + change.y())
            self.old_position = event.globalPos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        After dragging, restores the timer to its previous state (paused or running).
        """
        if self.drag_timer_was_active:
            if not self.session_finished:
                self.timer.stop()
                self._set_timer_visuals(False)
                if not self.was_timer_active:
                    self.pause()
            self.drag_timer_was_active = False
        # super().mouseReleaseEvent(event)


    def eventFilter(self, source, event):
        if self.session_finished and self.close_timer.isActive():
            if event.type() in (
                QtCore.QEvent.KeyPress,
                QtCore.QEvent.MouseButtonPress,
            ):
                self.cancel_close_countdown()

        if source is self.image_display:
            if event.type() == QtCore.QEvent.Gesture:
                return self._handle_pinch_gesture(event)

            if event.type() == QtCore.QEvent.NativeGesture:
                handled = self._handle_native_gesture(event)
                if handled:
                    return True

            if event.type() == QtCore.QEvent.Wheel:
                pixel_delta = event.pixelDelta()
                angle_delta = event.angleDelta()
                cursor_pos = event.pos()
                has_pixel = not pixel_delta.isNull()
                has_angle = angle_delta.y() != 0
                now_ms = int(QtCore.QDateTime.currentMSecsSinceEpoch())

                if self.zoom_enabled:
                    if now_ms < self.touchpad_zoom_active_until_ms:
                        return True
                    # Two-finger scroll pans while zoomed; pinch/native gesture handles zoom.
                    if has_pixel:
                        if self.zoom_factor > self.default_zoom_factor:
                            self._pan_by(QtCore.QPoint(pixel_delta.x(), pixel_delta.y()))
                        return True

                    if has_angle:
                        self.apply_zoom_input(
                            angle_delta.y(),
                            cursor_pos=cursor_pos,
                            source="wheel-angle",
                            timestamp_ms=int(
                                QtCore.QDateTime.currentMSecsSinceEpoch()
                            ),
                        )
                        return True
                    if has_pixel and pixel_delta.y() != 0:
                        self.apply_zoom_input(
                            pixel_delta.y(),
                            cursor_pos=cursor_pos,
                            source="wheel-pixel",
                            timestamp_ms=int(
                                QtCore.QDateTime.currentMSecsSinceEpoch()
                            ),
                        )
                        return True
                return True

            if event.type() == QtCore.QEvent.MouseButtonPress and (
                self.zoom_enabled
                and event.button() in (QtCore.Qt.LeftButton, QtCore.Qt.MiddleButton)
                and self.zoom_factor > self.default_zoom_factor
            ):
                self.is_panning = True
                self.pan_last_pos = event.pos()
                self.image_display.setCursor(QtCore.Qt.ClosedHandCursor)
                return True

            if event.type() == QtCore.QEvent.MouseMove and self.is_panning:
                delta = event.pos() - self.pan_last_pos
                self.pan_last_pos = event.pos()
                self._pan_by(delta)
                return True

            if event.type() == QtCore.QEvent.MouseButtonRelease and self.is_panning:
                self.is_panning = False
                self.image_display.setCursor(QtCore.Qt.OpenHandCursor)
                return True

            if event.type() == QtCore.QEvent.TabletPress and self.zoom_enabled:
                self.is_tablet_panning = True
                self.pan_last_pos = QtCore.QPoint(
                    int(event.posF().x()), int(event.posF().y())
                )
                self.image_display.setCursor(QtCore.Qt.ClosedHandCursor)
                return True

            if event.type() == QtCore.QEvent.TabletMove and self.is_tablet_panning:
                current_pos = QtCore.QPoint(int(event.posF().x()), int(event.posF().y()))
                delta = current_pos - self.pan_last_pos
                self.pan_last_pos = current_pos
                if event.modifiers() & QtCore.Qt.ControlModifier:
                    self.apply_zoom_input(
                        -delta.y() / 18.0,
                        cursor_pos=current_pos,
                        source="gesture",
                        timestamp_ms=int(QtCore.QDateTime.currentMSecsSinceEpoch()),
                    )
                elif self.zoom_factor > self.default_zoom_factor:
                    self._pan_by(delta)
                return True

            if event.type() == QtCore.QEvent.TabletRelease and self.is_tablet_panning:
                self.is_tablet_panning = False
                self.image_display.setCursor(QtCore.Qt.OpenHandCursor)
                return True

            if self.session_finished:
                if event.type() == QtCore.QEvent.MouseButtonDblClick:
                    self.open_image_directory(event)
                    return True
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    self.old_position = event.globalPos()
                    self.drag_start_position = event.globalPos()
                    return True
            else:
                if event.type() == QtCore.QEvent.MouseButtonDblClick:
                    if self.was_timer_active:
                        self.pause()  # Always pause on double click
                    self.time_seconds += 0.7
                    self.open_image_directory(event)
                    return True
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    self.old_position = event.globalPos()
                    self.drag_start_position = event.globalPos()
                    # Only toggle pause/resume if not part of a drag
                    if not self.drag_timer_was_active:
                        if self.timer.isActive():
                            self.timer.stop()
                            self._set_timer_visuals(False)
                        else:
                            self.timer.start(500)
                            self._set_timer_visuals(True)
                        self.display_time()
                    self.was_timer_active = self.timer.isActive()
                    self.drag_timer_was_active = False
                    return True
        return super(SessionDisplay, self).eventFilter(source, event)

    def skip_image(self):
        if self.playlist[self.playlist_position] == BREAK_IMAGE_PATH:
            print(f"No images to skip on break {self.playlist[self.playlist_position]}")
            self.setWindowTitle("No images to skip on break")
            return

        swap_indicies = list(range(self.playlist_position + 1, len(self.playlist)))
        random.shuffle(swap_indicies)
        while swap_indicies:
            swap_index = swap_indicies.pop()
            if self.playlist[swap_index] != BREAK_IMAGE_PATH:
                self.playlist[self.playlist_position], self.playlist[swap_index] = (
                    self.playlist[swap_index],
                    self.playlist[self.playlist_position],
                )
                break
        else:
            print(f"No images to skip to {self.playlist[self.playlist_position]}")
            self.setWindowTitle("No remaining unused images to skip to")
            return
        self.display_image()
        self.restart_timer()

    def toggle_mute(self):
        if self.mute is True:
            self.mute = False
            mixer.music.set_volume(self.volume)
        else:
            self.mute = True
            self.volume = mixer.music.get_volume()
            mixer.music.set_volume(0.0)

    def load_entry(self, resume_timer: bool = True):
        if self.entry["current"] >= self.entry["total"]:
            self.end_session()
            return
        self.entry["time"] = self.schedule[self.entry["current"]].time
        self.timer.stop()
        self.time_seconds = self.entry["time"]
        if resume_timer:
            self.timer.start(500)
            self._set_timer_visuals(True)
        else:
            self._set_timer_visuals(False)
        self.entry["amount of items"] = max(
            0, self.schedule[self.entry["current"]].images - 1
        )
        # Update entry_progress dot indicator
        self.entry_progress.setMaximum(self.entry["total"])
        self.entry_progress.setValue(self.entry["current"] + 1)
        self.display_image()

    def end_session(self):
        self.session_finished = True
        self.timer.stop()
        if hasattr(self, "idle_indicator_pulse_timer"):
            self.idle_indicator_pulse_timer.stop()
        # Prevent further countdown updates once the session is done
        self.timer.blockSignals(True)
        self.close_seconds = 15
        self.setWindowTitle("Session complete! Navigate images with arrows")
        self.session_info.setText(
            "Use arrows to browse. Double-click or Ctrl+O to open folder"
        )
        # Keep review mode anchored to the last scheduled slot (breaks included).
        self.playlist_position = self._last_scheduled_playlist_index()
        self._sync_entry_to_playlist_position()
        self.timer_display.setText(f"Done! Closing in {self.close_seconds}s...")
        # Grey-out / complete the bars
        self.image_progress.setValue(self.image_progress.maximum())
        self.entry_progress.setValue(self.entry_progress.maximum())
        self.update_close_title()
        self.close_timer.start(1000)

    def _last_scheduled_playlist_index(self):
        if not self.schedule or not self.playlist:
            return 0

        scheduled_slots = 0
        for schedule_entry in self.schedule:
            scheduled_slots += schedule_entry.images if schedule_entry.images > 0 else 1

        return max(0, min(len(self.playlist), scheduled_slots) - 1)

    def _sync_entry_to_playlist_position(self):
        if not self.schedule:
            return

        last_index = self._last_scheduled_playlist_index()
        pos = max(0, min(self.playlist_position, last_index))
        self.playlist_position = pos

        schedule_pos = 0
        for index, schedule_entry in enumerate(self.schedule):
            if schedule_entry.images <= 0:
                if schedule_pos == pos:
                    self.entry["current"] = index
                    self.entry["amount of items"] = 0
                    self.entry["time"] = schedule_entry.time
                    self.entry_progress.setMaximum(self.entry["total"])
                    self.entry_progress.setValue(index + 1)
                    return
                schedule_pos += 1
                continue

            start = schedule_pos
            end = start + schedule_entry.images
            if start <= pos < end:
                image_offset = pos - start
                self.entry["current"] = index
                self.entry["amount of items"] = schedule_entry.images - image_offset - 1
                self.entry["time"] = schedule_entry.time
                self.entry_progress.setMaximum(self.entry["total"])
                self.entry_progress.setValue(index + 1)
                return
            schedule_pos = end

        # Fallback to last entry if position falls outside expected bounds.
        last_index = len(self.schedule) - 1
        self.entry["current"] = last_index
        self.entry["time"] = self.schedule[last_index].time
        self.entry["amount of items"] = 0
        self.entry_progress.setMaximum(self.entry["total"])
        self.entry_progress.setValue(last_index + 1)

    def load_next_image(self):
        was_timer_active = self.timer.isActive()
        self.timer.stop()
        if self.session_finished:
            self.cancel_close_countdown()
            self.timer.blockSignals(True)
            last_index = self._last_scheduled_playlist_index()
            self.playlist_position = max(0, min(self.playlist_position, last_index))
            if self.playlist_position >= last_index:
                return
            self.playlist_position += 1
            self.display_image()
            return
        if self.entry["current"] >= self.entry["total"]:  # End of schedule
            return
        if self.entry["amount of items"] <= 0:  # End of entry or desynced counter
            self.entry["amount of items"] = 0
            self.entry["current"] += 1
            self.playlist_position += 1
            self.new_entry = True
            self.time_seconds = self.entry["time"]
            self.load_entry(was_timer_active)
        else:
            self.timer.stop()
            self.time_seconds = self.entry["time"]
            if was_timer_active:
                self.timer.start(500)
            self.playlist_position += 1
            self.entry["amount of items"] -= 1
            self.new_entry = False
            if self.entry["amount of items"] == 0:
                self.end_of_entry = True
            self.display_image()
        if was_timer_active:
            self.timer.start(500)
            self._set_timer_visuals(True)
        else:
            self._set_timer_visuals(False)

    def display_image(self, play_sound=True):
        if self.session_finished:
            self._sync_entry_to_playlist_position()
        print(self.entry)
        # Sounds
        if play_sound:
            if self.new_entry:
                with sound_file("new_entry.mp3") as p:
                    mixer.music.load(str(p))
                mixer.music.play()
                # self.new_entry = False
            elif self.entry["amount of items"] == 0:  # Last image in entry
                with sound_file("last_entry_image.mp3") as p:
                    mixer.music.load(str(p))
                mixer.music.play()
            elif self.entry["time"] > 10:
                with sound_file("new_image.mp3") as p:
                    mixer.music.load(str(p))
                mixer.music.play()

        if self.playlist_position >= len(self.playlist):  # Last image
            self.timer.stop()
            self.timer_display.setText(f"Done!")
            return
        else:
            # if (self.entry['amount of items'] == -1  # End of entry
            #         or os.path.basename(
            #             self.playlist[self.playlist_position]
            #         ) == 'break.png'):  # Break scheduled
            if (
                self.playlist[self.playlist_position] == BREAK_IMAGE_PATH
            ):  # Break scheduled
                """
                Since the end of an entry has been reached, or a break is scheduled,
                configure for break image.

                """
                self.image_mods["break"] = True
                self.image_mods["break_grayscale"] = True
                self.entry["amount of items"] = 0
                self.setWindowTitle("Break")
                self.session_info.setText("Break")
                # Set image progress to break mode (single orange dot)
                self.image_progress.setMaximum(0)
                self.image_progress.setValue(1)
            else:
                self.image_mods["break"] = False
                self.image_mods["break_grayscale"] = False
                self.setWindowTitle(self.playlist[self.playlist_position])
                current_entry = self.schedule[self.entry["current"]]
                self.session_info.setText(
                    f' {self.entry["current"] + 1}/{self.entry["total"]} | '
                    f'{current_entry.images - self.entry["amount of items"]}'
                    f"/{current_entry.images}"
                )
                current_img_index = current_entry.images - self.entry["amount of items"]
                self.image_progress.setMaximum(current_entry.images)
                self.image_progress.setValue(current_img_index)
                self._adjust_progressbar_width()  # <- make room for new dot count
            self.image_progress.trigger_focus_flash()
            self.entry_progress.trigger_focus_flash()
            self._reset_indicator_pulse_markers()
            #                 self.entry_progress.setFormat(
            #                     f"Entry {self.entry['current'] + 1}/{self.entry['total']}"
            # )
            # self.session_info.setText(
            #     f' {self.entry["current"] + 1}/{self.entry["total"]} | '
            #     f'{current_entry.images - self.entry["amount of items"]}'
            #     f"/{current_entry.images}"
            # )
            self.prepare_image_mods()

    def prepare_image_mods(self):
        """
        self.image gets modified depending on which value in self.image_mods
        is true.
        """
        self.reset_animation_state()
        image_path = self.playlist[self.playlist_position]

        if not self.image_mods["break"]:
            animated = self._cache_get(self.animation_cache, image_path)
            if animated is None:
                animated = self.load_animation_frames(image_path)
                if animated is not None:
                    self._cache_put(
                        self.animation_cache,
                        image_path,
                        animated,
                        self.max_animation_cache_entries,
                    )
            if animated is not None:
                frames, durations = animated
                self.animation_frames = frames
                self.animation_durations_ms = durations
                self.animation_frame_index = 0
                self.animation_source_path = image_path
                self._render_cvimage(self.animation_frames[0])
                if len(self.animation_frames) > 1:
                    self.animation_timer.start(self.animation_durations_ms[0])
                return

        cvimage = self._cache_get(self.still_image_cache, image_path)
        if cvimage is None:
            cvimage = self.decode_current_image()
            if cvimage is not None and cvimage.size > 0:
                self._cache_put(
                    self.still_image_cache,
                    image_path,
                    cvimage,
                    self.max_still_cache_entries,
                )
        if cvimage is None or cvimage.size == 0:
            print(f"Error: Could not load image at {image_path}")
            self.setWindowTitle("Error processing image")
            return
        self._render_cvimage(cvimage)

    def _advance_animation_frame(self):
        if not self.animation_frames or self.animation_source_path is None:
            return
        if self.playlist[self.playlist_position] != self.animation_source_path:
            self.reset_animation_state()
            return

        self.animation_frame_index = (self.animation_frame_index + 1) % len(
            self.animation_frames
        )
        self._render_cvimage(self.animation_frames[self.animation_frame_index])
        frame_delay = self.animation_durations_ms[self.animation_frame_index]
        self.animation_timer.start(frame_delay)

    def load_animation_frames(self, image_path):
        suffix = Path(image_path).suffix.lower()
        if suffix not in SUPPORTED_ANIMATED_TYPES:
            return None

        frames, durations = self.decode_animation_frames_with_pillow(image_path)
        if frames is not None:
            return frames, durations
        if durations is not None:
            return None

        frames, durations = self.decode_animation_frames_with_ffmpeg(image_path)
        if frames is not None:
            return frames, durations

        return None

    def decode_animation_frames_with_pillow(self, image_path):
        if Image is None or ImageSequence is None or image_path.startswith(":/"):
            return None, None

        try:
            with Image.open(image_path) as pil_image:
                frame_count = int(getattr(pil_image, "n_frames", 1))
                if frame_count <= 1:
                    return None, []

                frames = []
                durations = []
                base_duration = int(pil_image.info.get("duration", 100) or 100)
                for frame_idx in range(frame_count):
                    pil_image.seek(frame_idx)
                    rgba = np.array(pil_image.convert("RGBA"), dtype=np.uint8)
                    frames.append(cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
                    frame_duration = int(pil_image.info.get("duration", base_duration) or 100)
                    durations.append(max(20, frame_duration))
                return frames, durations
        except Exception:
            return None, None

    def decode_animation_frames_with_ffmpeg(self, image_path):
        if image_path.startswith(":/"):
            return None, None

        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            return None, None

        temp_dir = tempfile.mkdtemp(prefix="gesturesesh_anim_")
        try:
            frame_pattern = os.path.join(temp_dir, "frame_%06d.png")
            result = subprocess.run(
                [ffmpeg_path, "-v", "error", "-i", image_path, "-vsync", "0", frame_pattern],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode != 0:
                return None, None

            frame_paths = sorted(Path(temp_dir).glob("frame_*.png"))
            if len(frame_paths) <= 1:
                return None, None

            frames = []
            for frame_path in frame_paths:
                frame = cv2.imread(str(frame_path), cv2.IMREAD_UNCHANGED)
                if frame is None:
                    continue
                frames.append(self.normalize_cvimage_dtype(frame))
            if len(frames) <= 1:
                return None, None

            durations = [100] * len(frames)
            return frames, durations
        except Exception:
            return None, None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


    def _render_cvimage(self, cvimage):
        cvimage = self._apply_modifiers_to_cvimage(cvimage)
        if cvimage is None or cvimage.size == 0:
            self.setWindowTitle("Error processing image")
            return

        print(
            "cvimage shape:"
            f" {cvimage.shape}, channels: {1 if cvimage.ndim == 2 else cvimage.shape[2]}"
        )

        height, width = cvimage.shape[:2]
        if cvimage.ndim == 2:
            bytes_per_line = width
            self.image = QtGui.QImage(
                cvimage.data,
                width,
                height,
                bytes_per_line,
                QtGui.QImage.Format_Grayscale8,
            )
        else:
            channels = cvimage.shape[2]
            if channels == 4:
                cvimage = cv2.cvtColor(cvimage, cv2.COLOR_BGRA2RGBA)
                fmt = QtGui.QImage.Format_RGBA8888
            elif channels == 3:
                cvimage = cv2.cvtColor(cvimage, cv2.COLOR_BGR2RGB)
                fmt = QtGui.QImage.Format_RGB888
            else:
                self.setWindowTitle("Error processing image")
                return
            bytes_per_line = width * channels
            self.image = QtGui.QImage(cvimage.data, width, height, bytes_per_line, fmt)

        self.image = QtGui.QPixmap.fromImage(self.image)
        if self.reset_zoom_between_images:
            self.reset_zoom_pan()
        else:
            self.zoom_factor = max(
                self.min_zoom_factor, min(self.max_zoom_factor, self.zoom_factor)
            )
        if self.toggle_resize_status:
            self.image_scaled = self.image.scaled(
                self.image_display.size(),
                aspectRatioMode=QtCore.Qt.KeepAspectRatio,
                transformMode=QtCore.Qt.SmoothTransformation,
            )
            self.update_image_view()
            return

        if self.size() != self.previous_size:
            resized_pixmap = self.image_display.pixmap()
            scaled_size = self.scaling_size.scaled(
                resized_pixmap.size(), QtCore.Qt.KeepAspectRatio
            )
            self.scaling_size = QtCore.QSize(scaled_size)

        self.image_scaled = self.image.scaled(
            self.scaling_size,
            aspectRatioMode=QtCore.Qt.KeepAspectRatioByExpanding,
            transformMode=QtCore.Qt.SmoothTransformation,
        )
        self.update_image_view()
        self.image_display.resize(self.image_scaled.size())
        controls_height = self._controls_row_height()
        self.resize(
            self.image_scaled.size().width(),
            self.image_scaled.size().height() + controls_height,
        )
        self.previous_size = self.size()

    def decode_current_image(self):
        image_path = self.playlist[self.playlist_position]
        suffix = Path(image_path).suffix.lower()

        if suffix == ".jxl":
            decoders = (
                self.decode_with_cv2,
                self.decode_with_djxl,
                self.decode_with_pillow,
            )
        elif suffix in {".avif", ".gif", ".webp"}:
            decoders = (
                self.decode_with_cv2,
                self.decode_with_pillow,
                self.decode_with_djxl,
            )
        else:
            decoders = (
                self.decode_with_cv2,
                self.decode_with_pillow,
                self.decode_with_djxl,
            )

        for decoder in decoders:
            cvimage = decoder(image_path)
            if cvimage is not None and cvimage.size > 0:
                return self.normalize_cvimage_dtype(cvimage)

        return None

    def decode_with_cv2(self, image_path):
        try:
            if image_path.startswith(":/"):
                file = QtCore.QFile()
                file.setFileName(image_path)
                if not file.open(QtCore.QFile.OpenModeFlag.ReadOnly):
                    return None
                ba = file.readAll()
                ba = ba.data()
                file.close()
                file_bytes = np.asarray(bytearray(ba), dtype="uint8")
            else:
                with open(image_path, "rb") as f:
                    file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
            return cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
        except Exception:
            return None

    def decode_with_pillow(self, image_path):
        if Image is None or image_path.startswith(":/"):
            return None
        try:
            with Image.open(image_path) as pil_image:
                if ImageOps is not None:
                    pil_image = ImageOps.exif_transpose(pil_image)
                pil_image = pil_image.convert("RGBA")
                rgba = np.array(pil_image, dtype=np.uint8)
            return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
        except Exception:
            return None

    def decode_with_djxl(self, image_path):
        if Path(image_path).suffix.lower() != ".jxl" or image_path.startswith(":/"):
            return None
        djxl_path = shutil.which("djxl")
        if not djxl_path:
            return None

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_path = temp_file.name

            result = subprocess.run(
                [djxl_path, image_path, temp_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode != 0:
                return None

            return cv2.imread(temp_path, cv2.IMREAD_UNCHANGED)
        except Exception:
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def normalize_cvimage_dtype(self, cvimage):
        if cvimage.dtype == np.uint8:
            return cvimage

        if cvimage.dtype == np.bool_:
            return (cvimage.astype(np.uint8) * 255).astype(np.uint8)

        if np.issubdtype(cvimage.dtype, np.integer):
            min_val = int(cvimage.min())
            max_val = int(cvimage.max())
            if min_val < 0:
                return cv2.normalize(
                    cvimage, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U
                )
            if max_val <= 255:
                return cvimage.astype(np.uint8)
            if max_val <= 1023:
                scale_max = 1023
            elif max_val <= 4095:
                scale_max = 4095
            elif max_val <= 16383:
                scale_max = 16383
            else:
                scale_max = np.iinfo(cvimage.dtype).max
            return cv2.convertScaleAbs(cvimage, alpha=255.0 / scale_max)

        if np.issubdtype(cvimage.dtype, np.floating):
            min_val = float(cvimage.min())
            max_val = float(cvimage.max())
            if max_val <= 1.0 and min_val >= 0.0:
                return np.clip(cvimage * 255.0, 0, 255).astype(np.uint8)
            return cv2.normalize(
                cvimage, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U
            )

        return cvimage.astype(np.uint8)

    def convert_to_cvimage(self):
        return self.decode_with_cv2(self.playlist[self.playlist_position])


    def toggle_resize(self):
        if self.toggle_resize_status is not True:
            self.toggle_resize_status = True
            self.sizePolicy().setHeightForWidth(False)
        else:
            self.toggle_resize_status = False
            self.sizePolicy().setHeightForWidth(True)

    def toggle_always_on_top(self):
        if self.toggle_always_on_top_status is not True:
            self.toggle_always_on_top_status = True
            self.setWindowFlag(
                QtCore.Qt.X11BypassWindowManagerHint, self.toggle_always_on_top_status
            )
            self.setWindowFlag(
                QtCore.Qt.WindowStaysOnTopHint, self.toggle_always_on_top_status
            )
            self.show()
        else:
            self.toggle_always_on_top_status = False
            self.setWindowFlag(
                QtCore.Qt.X11BypassWindowManagerHint, self.toggle_always_on_top_status
            )
            self.setWindowFlag(
                QtCore.Qt.WindowStaysOnTopHint, self.toggle_always_on_top_status
            )
            self.show()

    def toggle_frameless(self):
        if self.frameless_status is not True:
            self.frameless_status = True
            self.setWindowFlag(QtCore.Qt.FramelessWindowHint, self.frameless_status)
            self.show()
        else:
            self.frameless_status = False
            self.setWindowFlag(QtCore.Qt.FramelessWindowHint, self.frameless_status)
            self.show()

    def previous_playlist_position(self):
        was_timer_active = self.timer.isActive()
        self.timer.stop()
        if self.session_finished:
            self.cancel_close_countdown()
            last_index = self._last_scheduled_playlist_index()
            self.playlist_position = max(0, min(self.playlist_position, last_index))
            if self.playlist_position == 0:
                self.display_image()
                self._set_timer_visuals(False)
                return
            self.playlist_position -= 1
            self.display_image()
            self._set_timer_visuals(False)
            return

        # First scheduled image
        if self.playlist_position == 0:
            """
            If it's the first image in the playlist or if the current entry
            is the first one and the position is at the beginning. The second
            case is in place for the skip function

            """
            self.time_seconds = self.entry["time"]
            self.update_timer_display()
            self.timer.stop()
            self.timer_display.setText("First image! Restarting timer...")
            QTest.qWait(1000)
            if was_timer_active:
                self.timer.start(500)
            self.load_entry(was_timer_active)
            self._set_timer_visuals(was_timer_active)
            return

        previous_entry_index = self.entry["current"]
        self.playlist_position -= 1
        self._sync_entry_to_playlist_position()
        self.new_entry = previous_entry_index != self.entry["current"]
        self.end_of_entry = self.entry["amount of items"] == 0
        self.time_seconds = self.entry["time"]
        self.update_timer_display()
        self.display_image()
        if was_timer_active:
            self.timer.start(500)
            self._set_timer_visuals(True)
        else:
            self._set_timer_visuals(False)

    # endregion

    # region Timer functions

    def open_image_directory(self, event=None):
        path = self.playlist[self.playlist_position]
        if path.startswith(":/"):
            return
        resolved_path = str(Path(path).resolve())
        system = platform.system()
        if system == "Windows":
            QtCore.QProcess.startDetached("explorer.exe", [f"/select,", resolved_path])
        elif system == "Darwin":  # macOS
            QtCore.QProcess.startDetached("open", ["-R", resolved_path])
        else:  # Linux and other systems
            # Use xdg-open for Linux
            parent_dir = Path(resolved_path).parent
            QtCore.QProcess.startDetached("xdg-open", [str(parent_dir)])
        if event:
            event.accept()

    # endregion
