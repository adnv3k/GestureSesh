"""Session display runtime for GestureSesh."""

from __future__ import annotations

import math
import random
import sys
from collections import OrderedDict

from pygame import mixer

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QWidget

from gesturesesh.session.constants import (
    BREAK_IMAGE_PATH,
    SUPPORTED_IMAGE_TYPES,
    sound_file,
)
from gesturesesh.app.selection_order import (
    real_image_paths,
    remaining_required_images,
)
from gesturesesh.session.image_loader import SessionImageLoaderMixin
from gesturesesh.session.image_mods import SessionImageModsMixin
from gesturesesh.session.shortcuts import SessionShortcutsMixin
from gesturesesh.session.timer import SessionTimerMixin
from gesturesesh.session.zoom_pan import SessionZoomPanMixin
from gesturesesh.utils import resources_config  # noqa: F401
from gesturesesh.utils.file_reveal import reveal_in_file_manager
from gesturesesh.ui.dialogs import (
    run_selection_order_dialog,
    run_shortcut_map_dialog,
    ShortcutMapDialog,
)
from gesturesesh.ui.dot_indicator import DotIndicator
from gesturesesh.ui.session_display import Ui_session_display


class SessionDisplay(
    SessionImageModsMixin,
    SessionImageLoaderMixin,
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
        self.init_image_mods()
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
        # Apply persisted session settings after init_image_mods so that
        # image_mods exists when apply_session_settings accesses it.
        if settings:
            try:
                self.apply_session_settings(settings)
            except Exception:
                pass
        self._restore_persisted_display_settings(settings)
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

    def _get_main_window_for_persistence(self):
        try:
            import __main__

            main_window = getattr(__main__, "window", None)
            if main_window is not None and hasattr(main_window, "config"):
                return main_window
        except Exception:
            pass
        return None

    def _restore_persisted_display_settings(self, settings=None):
        toggle_resize = None

        if isinstance(settings, dict):
            session_display = settings.get("session_display", {})
            if isinstance(session_display, dict) and "toggle_resize_status" in session_display:
                toggle_resize = bool(session_display.get("toggle_resize_status"))
            elif "toggle_resize_status" in settings:
                toggle_resize = bool(settings.get("toggle_resize_status"))

        if toggle_resize is None:
            main_window = self._get_main_window_for_persistence()
            if main_window is not None:
                try:
                    toggle_resize = bool(
                        main_window.config.get("session_display", {}).get(
                            "toggle_resize_status", self.toggle_resize_status
                        )
                    )
                except Exception:
                    toggle_resize = self.toggle_resize_status

        if toggle_resize is None:
            toggle_resize = self.toggle_resize_status

        self.toggle_resize_status = bool(toggle_resize)
        self.sizePolicy().setHeightForWidth(not self.toggle_resize_status)

    def _persist_display_settings(self):
        main_window = self._get_main_window_for_persistence()
        if main_window is None:
            return
        try:
            main_window.config.setdefault("session_display", {})[
                "toggle_resize_status"
            ] = bool(self.toggle_resize_status)
            from gesturesesh.utils.config import save_config

            save_config(main_window.config_path, main_window.config)
        except Exception:
            pass
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

        self.order_button = QtWidgets.QPushButton("Order", self)
        self.order_button.setToolTip(
            "View and manage session order.\nShortcut: Ctrl+Shift+I"
        )
        self.order_button.clicked.connect(self.open_session_order_viewer)

        for button in (
            self.zoom_toggle_button,
            self.order_button,
            self.shortcuts_button,
        ):
            button.setFocusPolicy(QtCore.Qt.NoFocus)
            button.setStyleSheet("background: rgb(119, 153, 146);")
            self.horizontalLayout_2.addWidget(button, 0, QtCore.Qt.AlignBottom)

        self.session_info.hide()

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
        self.order_button.setMinimumWidth(58)
        self.order_button.setFixedHeight(button_size.height())
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
        self.order_button.setFixedHeight(text_h)
        self.order_button.setMinimumWidth(52 if width <= 520 else 58)
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
        self.order_button.setVisible(not micro)
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
            # Clear the cached reference when the dialog closes, otherwise the
            # next toggle would call isVisible() on a wrapper whose C++ object
            # was already destroyed by WA_DeleteOnClose, fall into the except
            # branch, and open the blocking modal dialog instead.
            dlg.finished.connect(self._clear_shortcut_map_dialog)
            dlg.show()
            dlg.raise_()
            self._shortcut_map_dialog = dlg
        except Exception:
            # fallback to the blocking dialog
            try:
                run_shortcut_map_dialog(parent=self, shortcut_rows=self.shortcut_map_rows)
            except Exception:
                pass

    def _clear_shortcut_map_dialog(self, *_args):
        self._shortcut_map_dialog = None

    def _validate_session_order(self, files):
        required = remaining_required_images(
            self.schedule, self.playlist, self.playlist_position
        )
        available = len(real_image_paths(files[self.playlist_position :]))
        if available < required:
            return (
                "The session still needs "
                f"{required} image(s) from the current point forward, but this order "
                f"only has {available}. Add images or undo removals before applying."
            )
        return None

    def open_session_order_viewer(self):
        was_timer_active = self.timer.isActive()
        if not self.session_finished and was_timer_active:
            self.timer.stop()
            self._set_timer_visuals(False)

        result = run_selection_order_dialog(
            parent=self,
            files=self.playlist,
            schedule=self.schedule,
            valid_file_types=SUPPORTED_IMAGE_TYPES,
            locked_until=self.playlist_position if not self.session_finished else -1,
            current_index=self.playlist_position,
            validate_files=None if self.session_finished else self._validate_session_order,
            title="Session Order",
        )
        if result is not None:
            self.playlist = result["files"]
            self.clear_decode_caches()
            self._sync_entry_to_playlist_position()
            self.display_image(play_sound=False)

        if not self.session_finished and was_timer_active:
            self.timer.start(500)
            self._set_timer_visuals(True)

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
        else:
            self.image_scaled = None
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
        # If closing while in frameless fullscreen, restore the pre-fullscreen
        # window-state attributes so the persisted snapshot reflects what the
        # user actually had configured before entering fullscreen.
        if getattr(self, "_fullscreen_frameless", False):
            self.frameless_status = bool(getattr(self, "_prev_frameless_status", False))
            self.toggle_resize_status = bool(
                getattr(self, "_prev_toggle_resize_status", False)
            )
            self._fullscreen_frameless = False
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

    def toggle_resize(self):
        if self.toggle_resize_status is not True:
            self.toggle_resize_status = True
            self.sizePolicy().setHeightForWidth(False)
        else:
            self.toggle_resize_status = False
            self.sizePolicy().setHeightForWidth(True)
        self._persist_display_settings()

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

    def toggle_fullscreen_frameless(self):
        """Enter or exit frameless fullscreen mode with no window chrome."""
        if not getattr(self, "_fullscreen_frameless", False):
            # Enter frameless fullscreen.
            self._fullscreen_frameless = True

            # Remember exact previous window state so exit can restore it cleanly.
            self._prev_geometry = self.geometry()
            self._prev_window_state = self.windowState()
            self._prev_frameless_status = self.frameless_status
            self._prev_toggle_resize_status = getattr(self, "toggle_resize_status", False)
            self._prev_height_for_width = self.sizePolicy().hasHeightForWidth()

            try:
                # Frameless fullscreen should fit the whole image inside the screen
                # without overwriting the user's persisted normal-session preference.
                self.toggle_resize_status = True
                self.sizePolicy().setHeightForWidth(False)
                self.image_scaled = None
            except Exception:
                pass

            try:
                self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
                self.frameless_status = True
                self.showFullScreen()
            except Exception:
                self.showFullScreen()

            try:
                QtCore.QTimer.singleShot(0, self._refresh_image_for_window_change)
                QtCore.QTimer.singleShot(60, self._refresh_image_for_window_change)
            except Exception:
                pass

            try:
                self._show_temporary_indicator("Frameless fullscreen: On", ms=1000)
            except Exception:
                pass

            return

        # Exit frameless fullscreen.
        self._fullscreen_frameless = False

        try:
            self.toggle_resize_status = bool(
                getattr(self, "_prev_toggle_resize_status", False)
            )
            self.sizePolicy().setHeightForWidth(
                bool(getattr(self, "_prev_height_for_width", True))
            )
            self.image_scaled = None
        except Exception:
            pass

        restored_frameless = bool(getattr(self, "_prev_frameless_status", False))
        prev_geometry = getattr(self, "_prev_geometry", None)
        prev_window_state = getattr(self, "_prev_window_state", QtCore.Qt.WindowNoState)

        def restore_windowed_state():
            try:
                self.setWindowFlag(QtCore.Qt.FramelessWindowHint, restored_frameless)
                self.frameless_status = restored_frameless
            except Exception:
                pass

            try:
                self.showNormal()

                if prev_geometry is not None:
                    self.setGeometry(prev_geometry)

                if prev_window_state not in (
                    QtCore.Qt.WindowFullScreen,
                    QtCore.Qt.WindowNoState,
                ):
                    self.setWindowState(prev_window_state & ~QtCore.Qt.WindowFullScreen)

                self.show()
                self.raise_()
                self.activateWindow()
            except Exception:
                pass

            try:
                QtCore.QTimer.singleShot(0, self._refresh_image_for_window_change)
                QtCore.QTimer.singleShot(60, self._refresh_image_for_window_change)
            except Exception:
                pass

            try:
                self._show_temporary_indicator("Frameless fullscreen: Off", ms=800)
            except Exception:
                pass

        try:
            self.showNormal()
        except Exception:
            pass

        QtCore.QTimer.singleShot(0, restore_windowed_state)

    def _refresh_image_for_window_change(self):
        try:
            self.image_scaled = None
        except Exception:
            pass
        try:
            self.update_image_view()
        except Exception:
            pass

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
        if reveal_in_file_manager(path) and event:
            event.accept()

    # endregion
