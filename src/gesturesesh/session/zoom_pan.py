"""Zoom, pan, pinch-gesture, and image-view rendering for SessionDisplay."""

from __future__ import annotations

import math

from PyQt5 import QtCore, QtGui, QtWidgets


class SessionZoomPanMixin:
    """Zoom/pan interaction state and rendering, mixed into ``SessionDisplay``."""

    def init_zoom_pan(self):
        """Initialize zoom/pan interaction state for the slideshow image."""
        self.zoom_enabled = False
        self.reset_zoom_between_images = True
        self.default_zoom_factor = 1.0
        self.zoom_factor = self.default_zoom_factor
        self.min_zoom_factor = 0.75
        self.max_zoom_factor = 4.0
        self.base_zoom_step = 1.14
        self.zoom_step = self.base_zoom_step
        self.quick_inspect_zoom = 2.2
        self.pan_offset = QtCore.QPoint(0, 0)
        self.is_panning = False
        self.is_tablet_panning = False
        self.pan_last_pos = QtCore.QPoint(0, 0)
        self.last_zoom_input_ms = 0
        self.zoom_snap_timestamp_ms = 0
        self.touchpad_zoom_active_until_ms = 0
        self.pinch_start_zoom_factor = self.default_zoom_factor

        self.idle_indicator_pulse_timer = QtCore.QTimer(self)
        self.idle_indicator_pulse_timer.setSingleShot(False)
        self.idle_indicator_pulse_timer.timeout.connect(self._pulse_indicators_softly)

    def reset_zoom_pan(self):
        """Reset zoom/pan to defaults when showing a new image."""
        if not hasattr(self, "default_zoom_factor"):
            self.init_zoom_pan()
        self.zoom_factor = self.default_zoom_factor
        self.pan_offset = QtCore.QPoint(0, 0)
        self.is_panning = False
        self.is_tablet_panning = False

    def _clamp_pan_offset(self, offset: QtCore.QPoint, zoomed_size: QtCore.QSize):
        """Clamp panning so the zoomed image always covers the viewport."""
        viewport = self.image_display.size()
        max_x = max(0, (zoomed_size.width() - viewport.width()) // 2)
        max_y = max(0, (zoomed_size.height() - viewport.height()) // 2)
        return QtCore.QPoint(
            max(-max_x, min(offset.x(), max_x)),
            max(-max_y, min(offset.y(), max_y)),
        )

    def update_image_view(self):
        """Render the current image applying zoom and pan transforms."""
        if not hasattr(self, "image") or self.image.isNull():
            return

        target_size = self.image_display.size()
        aspect_mode = (
            QtCore.Qt.KeepAspectRatio
            if self.toggle_resize_status
            else QtCore.Qt.KeepAspectRatioByExpanding
        )

        # Only reuse cached scaling while in frameless fullscreen.
        # In normal session flow, always rescale against the current widget size
        # so the window keeps its original behavior and does not drift larger.
        use_cached = (
            getattr(self, "_fullscreen_frameless", False)
            and isinstance(getattr(self, "image_scaled", None), QtGui.QPixmap)
            and not self.image_scaled.isNull()
            and self.image_scaled.size() == target_size
        )

        if use_cached:
            base_pixmap = self.image_scaled
        else:
            base_pixmap = self.image.scaled(
                target_size,
                aspectRatioMode=aspect_mode,
                transformMode=QtCore.Qt.SmoothTransformation,
            )
            if getattr(self, "_fullscreen_frameless", False):
                self.image_scaled = base_pixmap
            else:
                self.image_scaled = None

        if not self.zoom_enabled:
            self.zoom_factor = self.default_zoom_factor
            self.pan_offset = QtCore.QPoint(0, 0)
            self.image_display.setPixmap(base_pixmap)
            return

        if abs(self.zoom_factor - self.default_zoom_factor) < 0.0001:
            self.pan_offset = QtCore.QPoint(0, 0)
            self.image_display.setPixmap(base_pixmap)
            return

        zoomed_size = QtCore.QSize(
            int(base_pixmap.width() * self.zoom_factor),
            int(base_pixmap.height() * self.zoom_factor),
        )
        zoomed = base_pixmap.scaled(
            zoomed_size,
            aspectRatioMode=QtCore.Qt.IgnoreAspectRatio,
            transformMode=QtCore.Qt.SmoothTransformation,
        )
        self.pan_offset = self._clamp_pan_offset(self.pan_offset, zoomed_size)

        viewport = QtGui.QPixmap(self.image_display.size())
        viewport.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(viewport)
        draw_x = (viewport.width() - zoomed.width()) // 2 + self.pan_offset.x()
        draw_y = (viewport.height() - zoomed.height()) // 2 + self.pan_offset.y()
        painter.drawPixmap(draw_x, draw_y, zoomed)
        painter.end()
        self.image_display.setPixmap(viewport)

    def _zoom_velocity_multiplier(self, units, timestamp_ms):
        if timestamp_ms is None:
            timestamp_ms = int(QtCore.QDateTime.currentMSecsSinceEpoch())
        if self.last_zoom_input_ms == 0:
            self.last_zoom_input_ms = timestamp_ms
            return 1.0
        delta_ms = max(1, timestamp_ms - self.last_zoom_input_ms)
        self.last_zoom_input_ms = timestamp_ms
        units_per_second = abs(units) * 1000.0 / delta_ms
        return min(2.2, max(0.8, 0.9 + units_per_second * 0.16))

    def _zoom_slowdown_multiplier(self, zoom_in: bool):
        if zoom_in:
            remaining = self.max_zoom_factor - self.zoom_factor
            span = max(0.0001, self.max_zoom_factor - self.default_zoom_factor)
        else:
            remaining = self.zoom_factor - self.min_zoom_factor
            span = max(0.0001, self.default_zoom_factor - self.min_zoom_factor)

        normalized = max(0.0, min(1.0, remaining / span))
        return max(0.08, normalized**0.55)

    def _zoom_at_cursor(self, target_zoom, cursor_pos=None):
        target_zoom = max(self.min_zoom_factor, min(self.max_zoom_factor, target_zoom))
        if not hasattr(self, "image"):
            return

        if hasattr(self, "image_scaled") and isinstance(
            self.image_scaled, QtGui.QPixmap
        ):
            base_pixmap = self.image_scaled
        else:
            base_pixmap = self.image.scaled(
                self.image_display.size(),
                aspectRatioMode=QtCore.Qt.KeepAspectRatio
                if self.toggle_resize_status
                else QtCore.Qt.KeepAspectRatioByExpanding,
                transformMode=QtCore.Qt.SmoothTransformation,
            )

        viewport_w = max(1, self.image_display.width())
        viewport_h = max(1, self.image_display.height())
        if cursor_pos is None:
            cursor_pos = QtCore.QPoint(viewport_w // 2, viewport_h // 2)

        old_zoom = max(0.0001, self.zoom_factor)
        old_zoomed_w = base_pixmap.width() * old_zoom
        old_zoomed_h = base_pixmap.height() * old_zoom
        old_draw_x = (viewport_w - old_zoomed_w) / 2 + self.pan_offset.x()
        old_draw_y = (viewport_h - old_zoomed_h) / 2 + self.pan_offset.y()
        source_x = (cursor_pos.x() - old_draw_x) / old_zoom
        source_y = (cursor_pos.y() - old_draw_y) / old_zoom

        new_zoomed_w = base_pixmap.width() * target_zoom
        new_zoomed_h = base_pixmap.height() * target_zoom
        new_draw_x = cursor_pos.x() - source_x * target_zoom
        new_draw_y = cursor_pos.y() - source_y * target_zoom
        pan_x = new_draw_x - (viewport_w - new_zoomed_w) / 2
        pan_y = new_draw_y - (viewport_h - new_zoomed_h) / 2

        self.zoom_factor = target_zoom
        self.pan_offset = QtCore.QPoint(int(round(pan_x)), int(round(pan_y)))
        self.pan_offset = self._clamp_pan_offset(
            self.pan_offset,
            QtCore.QSize(int(new_zoomed_w), int(new_zoomed_h)),
        )
        self.update_image_view()

    def apply_zoom_input(self, raw_delta, cursor_pos=None, source="wheel", timestamp_ms=None):
        if not self.zoom_enabled or raw_delta == 0:
            return

        if timestamp_ms is None:
            timestamp_ms = int(QtCore.QDateTime.currentMSecsSinceEpoch())

        if source == "wheel-angle":
            units = raw_delta / 120.0
        elif source == "wheel-pixel":
            units = raw_delta / 60.0
        else:
            units = raw_delta
        if abs(units) < 0.001:
            return

        zoom_in = units > 0
        if (
            not zoom_in
            and self.zoom_factor <= self.default_zoom_factor + 0.001
            and timestamp_ms - self.zoom_snap_timestamp_ms < 140
        ):
            return

        speed_mult = self._zoom_velocity_multiplier(units, timestamp_ms)
        slow_mult = self._zoom_slowdown_multiplier(zoom_in)
        effective_units = abs(units) * speed_mult * slow_mult
        step_factor = self.base_zoom_step**effective_units
        target_zoom = (
            self.zoom_factor * step_factor
            if zoom_in
            else self.zoom_factor / max(0.0001, step_factor)
        )
        if (
            not zoom_in
            and self.zoom_factor > self.default_zoom_factor
            and speed_mult >= 1.20
            and target_zoom <= self.default_zoom_factor * 1.05
        ):
            target_zoom = self.default_zoom_factor
            self.zoom_snap_timestamp_ms = timestamp_ms
        else:
            target_zoom = max(self.min_zoom_factor, min(self.max_zoom_factor, target_zoom))

        if abs(target_zoom - self.zoom_factor) < 0.0005:
            return
        self._zoom_at_cursor(target_zoom, cursor_pos)

    def zoom_image(self, zoom_in: bool, cursor_pos=None):
        """Discrete zoom command with cursor-centered behavior."""
        self.apply_zoom_input(
            1.0 if zoom_in else -1.0,
            cursor_pos=cursor_pos,
            source="discrete",
            timestamp_ms=int(QtCore.QDateTime.currentMSecsSinceEpoch()),
        )

    def reset_zoom_to_default(self):
        self.reset_zoom_pan()
        self.update_image_view()

    def toggle_zoom_enabled(self, checked=None):
        if checked is None:
            checked = not self.zoom_enabled
        self.zoom_enabled = bool(checked)
        if hasattr(self, "zoom_toggle_button"):
            self.zoom_toggle_button.setChecked(self.zoom_enabled)
            self.zoom_toggle_button.setStyleSheet(
                "background: rgb(68,201,176);" if self.zoom_enabled else "background: rgb(119, 153, 146);"
            )
        if not self.zoom_enabled:
            self.reset_zoom_to_default()
        self.image_display.setCursor(
            QtCore.Qt.OpenHandCursor if self.zoom_enabled else QtCore.Qt.ArrowCursor
        )

    def toggle_zoom_reset_mode(self):
        self.reset_zoom_between_images = not self.reset_zoom_between_images
        mode = "ON" if self.reset_zoom_between_images else "OFF"
        self.setWindowTitle(f"Auto zoom reset: {mode}")

    def quick_inspect(self):
        if not self.zoom_enabled:
            self.toggle_zoom_enabled(True)
        target = (
            self.quick_inspect_zoom
            if self.zoom_factor <= self.default_zoom_factor + 0.05
            else self.default_zoom_factor
        )
        self._zoom_at_cursor(target, QtCore.QPoint(self.image_display.width() // 2, self.image_display.height() // 2))

    def _pan_by(self, delta_point):
        if not self.zoom_enabled or self.zoom_factor <= self.default_zoom_factor:
            return
        self.pan_offset += delta_point
        self.update_image_view()

    def _handle_pinch_gesture(self, gesture_event):
        pinch = gesture_event.gesture(QtCore.Qt.PinchGesture)
        if pinch is None:
            return False
        if not self.zoom_enabled:
            return True

        state = pinch.state()
        if state == QtCore.Qt.GestureStarted:
            self.pinch_start_zoom_factor = self.zoom_factor
        elif state == QtCore.Qt.GestureFinished:
            self.pinch_start_zoom_factor = self.zoom_factor
            self.touchpad_zoom_active_until_ms = int(
                QtCore.QDateTime.currentMSecsSinceEpoch()
            ) + 160
            return True

        if state not in (QtCore.Qt.GestureStarted, QtCore.Qt.GestureUpdated):
            return True

        if pinch.changeFlags() & QtWidgets.QPinchGesture.ScaleFactorChanged:
            total_factor = float(pinch.totalScaleFactor() or 1.0)
            if total_factor > 0:
                target_zoom = self.pinch_start_zoom_factor * total_factor
                center = pinch.centerPoint().toPoint()
                center = self.image_display.mapFromGlobal(center)
                self._zoom_at_cursor(target_zoom, center)
                self.touchpad_zoom_active_until_ms = int(
                    QtCore.QDateTime.currentMSecsSinceEpoch()
                ) + 160
        return True

    def _handle_native_gesture(self, event):
        if not self.zoom_enabled:
            return True
        if not hasattr(event, "gestureType"):
            return False
        zoom_native = getattr(QtCore.Qt, "ZoomNativeGesture", None)
        if zoom_native is not None and event.gestureType() == zoom_native:
            delta = float(event.value())
            if abs(delta) > 0.0002:
                cursor = self.image_display.mapFromGlobal(QtGui.QCursor.pos())
                factor = math.exp(delta * 0.85)
                target_zoom = self.zoom_factor * factor
                self._zoom_at_cursor(target_zoom, cursor)
                self.touchpad_zoom_active_until_ms = int(
                    QtCore.QDateTime.currentMSecsSinceEpoch()
                ) + 160
            return True
        return False
