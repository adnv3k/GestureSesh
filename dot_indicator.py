# dot_indicator.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from PyQt5 import QtCore, QtGui, QtWidgets

# ════════════════════════════════════════════════════════════════════════════
# THEME SUPPORT (REVISION 2025-06-16 s)
# ---------------------------------------------------------------------------
# • Centralise *all* colour definitions in a single @dataclass (DotPalette).
# • Palette values are expressed purely as HSLA tuples → trivial to retheme.
# • DotIndicator now accepts an optional palette parameter; supplying a custom
#   palette instantly reskins the widget with no further code changes.
# ════════════════════════════════════════════════════════════════════════════


@dataclass
class DotPalette:
    """H S L [A] values for every visual state in one place (ease of theming)."""

    current: tuple[int, float, float, float] = (174, 0.87, 0.61, 1.0)
    passed: tuple[int, float, float, float] = (173, 0.70, 0.24, 1.0)
    empty: tuple[int, float, float, float] = (207, 0.22, 0.22, 1.0)
    break_on: tuple[int, float, float, float] = (34, 1.00, 0.60, 1.0)
    break_off: tuple[int, float, float, float] = (34, 0.96, 0.24, 1.0)
    chevron: tuple[int, float, float, float] = (182, 1.00, 0.69, 1.0)

    @staticmethod
    def _tuple_to_qcolor(hsla: Iterable[float | int]) -> QtGui.QColor:
        h, s, l, *a = hsla
        qcol = QtGui.QColor()
        qcol.setHslF(h / 360, s, l, a[0] if a else 1.0)
        return qcol

    # Convert every HSLA spec into a ready-to-use QColor -------------------
    def as_qcolors(self):
        return {
            name: self._tuple_to_qcolor(value) for name, value in self.__dict__.items()
        }


class DotIndicator(QtWidgets.QWidget):
    """
    Progress row (≤ 10 images per set).

    • Dots 1-9 track images (or entries) within the *current* 10-slot block.
    • Slot #10 morphs into a right-pointing chevron when *any* images remain
      after this block; while on image #10 it fills and pulses once per
      remaining block (⌈remaining / 10⌉ pulses).

    Break handling
    ──────────────
    *Row break* (`maximum ≤ 0`) or *per-dot break* always draws **one orange
    dot** in the images row.  **Default state is dim**; the dot brightens only
    while current and dims again once passed.

    ──────────────────────────────────────────────────────────────────────────
    REVISION 2025-06-16 s ← THIS UPDATE (Theme-ready palette system)
    • **DotPalette** dataclass centralises colours in HSLA for effortless
      theming.  Pass `palette=DotPalette( … )` to recolour instantly.
    REVISION 2025-06-16 r
    • **De-clipped overlay glow** – when `top_overlay=True`, the widget now
      reserves just enough extra space *below* the dots for the halo to spill
      onto the entries row **without** enlarging the control bar’s perceived
      height.  (See `extra_pad` block.)
    REVISION 2025-06-16 q
    • **Fixed-height policy** – the widget clamps its minimum *and* maximum
      height to one value and uses `QSizePolicy.Fixed` vertically.
    REVISION 2025-06-15 p
    • **Top-flush layout** – dots hug the widget’s top (old gap removed).
    • **Dynamic centring** – rows with < 9 dots are centred horizontally.
    • **Last-dot marker** – final dot of a sub-entry is ring-highlighted.
    REVISION 2025-06-15 o
    • **Fail-safe row-break reset**, guard in `setValue`, and auto-stopping
      pulse timer on breaks.
    """

    # ─────────────────────── Tunables (class defaults) ────────────────────
    DEFAULT_DOT_D = 8
    DEFAULT_DOT_SPC = 5
    DEFAULT_CHEV_SCALE_W = 0.65
    DEFAULT_CHEV_SCALE_H = 0.65
    DEFAULT_CHEV_CORE_W = 4
    DEFAULT_GLOW_LAYERS = [2, 1.4, 0.9]

    # ───────────────────────────── Init ───────────────────────────────────
    def __init__(
        self,
        *,
        palette: DotPalette | None = None,
        parent: QtWidgets.QWidget | None = None,
        dot_d: int | None = None,
        dot_spc: int | None = None,
        chev_scale_w: float | None = None,
        chev_scale_h: float | None = None,
        chev_core_w: int | None = None,
        glow_layers: list[float] | None = None,
        top_overlay: bool = False,
        align_top: bool = True,
    ):
        super().__init__(parent)

        # 1.  Theme palette -------------------------------------------------
        self._palette_dict = (palette or DotPalette()).as_qcolors()
        self._current_color = self._palette_dict["current"]
        self._passed_color = self._palette_dict["passed"]
        self._empty_color = self._palette_dict["empty"]
        self._break_color = self._palette_dict["break_on"]
        self._break_passed_color = self._palette_dict["break_off"]
        self._chevron_color = self._palette_dict["chevron"]
        self._glow_color = self._chevron_color  # Glow tracks chevron

        # 2.  Geometry overrides -------------------------------------------
        self._DOT_D = dot_d or self.DEFAULT_DOT_D
        self._DOT_SPC = dot_spc or self.DEFAULT_DOT_SPC
        self._chev_scale_w = chev_scale_w or self.DEFAULT_CHEV_SCALE_W
        self._chev_scale_h = chev_scale_h or self.DEFAULT_CHEV_SCALE_H
        self._chev_core_w = chev_core_w or self.DEFAULT_CHEV_CORE_W
        self._glow_layers = glow_layers or self.DEFAULT_GLOW_LAYERS
        self._align_top = align_top

        # 3.  Optional overlay mode ----------------------------------------
        if top_overlay:
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
            self.setFocusPolicy(QtCore.Qt.NoFocus)
            self.raise_()

        # 4.  Pulse machinery ----------------------------------------------
        self._flash_strength = 0.0
        self._pulse_dir = 1
        self._pulses_left = 0
        self._pulse_timer = QtCore.QTimer(self, interval=50)
        self._pulse_timer.timeout.connect(self._on_pulse_tick)

        # 5.  Progress state -----------------------------------------------
        self._max_value = 1  # total images (0 → row break)
        self._value = 1  # current (1-based)
        self._break_indices: set[int] = set()

        # 6.  Layout metrics & fixed height --------------------------------
        stroke_max = self._chev_core_w * max(self._glow_layers)
        self._glow_pad = math.ceil(2 + stroke_max / 2)

        halo_thickness = max(self._glow_layers) * 2
        extra_pad = math.ceil(halo_thickness + 1) if top_overlay else 0
        fixed_h = self._DOT_D + self._glow_pad + extra_pad

        self.setMinimumHeight(fixed_h - 2)
        self.setMaximumHeight(fixed_h - 2)
        # self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)

    # ---------------------------------------------------------------------
    #                           Public API
    # ---------------------------------------------------------------------
    def setMaximum(self, maximum: int):
        """`maximum>0`→normal. `maximum≤0`→entire row is a break dot."""
        self._max_value = max(0, maximum)
        if self._is_row_break():
            self._value = 1
            self._pulse_timer.stop()
            self._flash_strength = 0.0
        self.updateGeometry()
        self.update()

    def setValue(self, value: int):
        """1-based current index inside this row."""
        self._value = max(1, value)
        if self._is_row_break():
            self._value = 1
            self._flash_strength = 0.0
            self._pulse_dir = 1
            self._pulses_left = float("inf")
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
            return

        dots_count, has_chevron, _ = self._layout_counts()
        sets_remaining = self._sets_left_after_current_set()

        offset = self._value - self._current_set_start() - 1
        local_breaks = {
            i - self._current_set_start()
            for i in self._break_indices
            if self._current_set_start() <= i < self._current_set_start() + dots_count
        }
        is_current_break = offset in local_breaks

        if sets_remaining > 0 and not is_current_break:
            self._flash_strength = 0.0
            self._pulse_dir = 1
            self._pulses_left = sets_remaining
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        elif is_current_break:
            self._flash_strength = 0.0
            self._pulse_dir = 1
            self._pulses_left = float("inf")
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            if self._pulse_timer.isActive():
                self._pulse_timer.stop()
            self._flash_strength = 0.0

        self.update()

    def setBreaks(self, break_indices):
        """Mark 0-based indices that are always drawn as break dots."""
        self._break_indices = set(break_indices)
        self.update()

    def applyBreakVector(self, counts: list[int]):
        """Flag every index whose count ≤ 0 as a break."""
        self._break_indices = {i for i, c in enumerate(counts) if c <= 0}
        self.setMaximum(len(counts))
        self.update()

    # ---------------------------------------------------------------------
    #                           Internals
    # ---------------------------------------------------------------------
    def _is_row_break(self) -> bool:
        return self._max_value == 0

    def _current_set_start(self) -> int:
        return ((self._value - 1) // 10) * 10

    def _sets_left_after_current_set(self) -> int:
        if self._is_row_break():
            return 0
        remaining = self._max_value - (self._current_set_start() + 10)
        return math.ceil(max(0, remaining) / 10)

    def _layout_counts(self):
        """Return (dots_count, has_chevron, set_start)."""
        if self._is_row_break():
            return 1, False, 0

        set_start = self._current_set_start()
        images_in_set = min(10, self._max_value - set_start)
        has_chevron = self._max_value - (set_start + 10) > 0
        dots_count = images_in_set - (1 if has_chevron else 0)
        return dots_count, has_chevron, set_start

    def _row_width(self, dots_count: int, has_chevron: bool) -> int:
        width = dots_count * self._DOT_D
        if dots_count > 0:
            width += (dots_count - 1) * self._DOT_SPC
        if has_chevron:
            width += self._DOT_SPC + int(self._DOT_D * self._chev_scale_w)
        return width

    # Keep legacy constant width for overall layout stability
    def _full_width(self) -> int:
        dots_w = 9 * self._DOT_D + 8 * self._DOT_SPC
        chev_w = int(self._DOT_D * self._chev_scale_w) + self._DOT_SPC
        return self._glow_pad * 2 + dots_w + chev_w

    def sizeHint(self):
        return QtCore.QSize(self._full_width(), self.minimumHeight())

    minimumSizeHint = sizeHint  # alias

    # ---------------------------------------------------------------------
    #                       Pulse animation
    # ---------------------------------------------------------------------
    def _on_pulse_tick(self):
        self._flash_strength += self._pulse_dir * 0.1
        if self._flash_strength >= 1.0:
            self._flash_strength, self._pulse_dir = 1.0, -1
        elif self._flash_strength <= 0.0:
            self._flash_strength, self._pulse_dir = 0.0, 1
            if self._pulses_left != float("inf"):
                self._pulses_left -= 1
                if self._pulses_left <= 0:
                    self._pulse_timer.stop()
        self.update()

    # ---------------------------------------------------------------------
    #                           Painting
    # ---------------------------------------------------------------------
    def paintEvent(self, _: QtGui.QPaintEvent):  # noqa: C901  (long but clear)
        dots_count, has_chevron, set_start = self._layout_counts()
        if dots_count + (1 if has_chevron else 0) == 0:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # ───── Row-break (single orange dot) ──────────────────────────────
        if self._is_row_break():
            y0 = (
                self._glow_pad
                if self._align_top
                else (
                    self._glow_pad
                    + (self.height() - self._glow_pad * 2 - self._DOT_D) / 2
                )
            )
            x = self._glow_pad + (self.width() - self._glow_pad * 2 - self._DOT_D) / 2
            color = self._break_color if self._value == 1 else self._break_passed_color

            if self._value == 1 and self._flash_strength > 0.0:
                for factor in self._glow_layers:
                    glow_d = self._DOT_D + factor * 4
                    glow_rect = QtCore.QRectF(
                        x + (self._DOT_D - glow_d) / 2,
                        y0 + (self._DOT_D - glow_d) / 2,
                        glow_d,
                        glow_d,
                    )
                    glow_col = QtGui.QColor(self._break_color)
                    alpha = self._flash_strength * (0.4 / factor + 0.1)
                    glow_col.setAlpha(int(alpha * 255))
                    painter.setPen(QtCore.Qt.NoPen)
                    painter.setBrush(glow_col)
                    painter.drawEllipse(glow_rect)

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QtCore.QRectF(x, y0, self._DOT_D, self._DOT_D))
            return

        # ───── Normal row (dots + optional chevron) ───────────────────────
        row_h = int(self._DOT_D * (self._chev_scale_h if has_chevron else 1.0))
        y0 = (
            self._glow_pad
            if self._align_top
            else (self._glow_pad + (self.height() - self._glow_pad * 2 - row_h) / 2)
        )

        row_total_w = self._row_width(dots_count, has_chevron)
        x = self._glow_pad + (self.width() - self._glow_pad * 2 - row_total_w) / 2

        offset = self._value - set_start - 1
        chevron_filled = has_chevron and offset == 9
        current_dot = offset if offset < dots_count else None
        passed_dots = (
            dots_count if chevron_filled else max(0, min(offset, dots_count - 1))
        )

        local_breaks = {
            i - set_start
            for i in self._break_indices
            if set_start <= i < set_start + dots_count
        }

        # Draw dots --------------------------------------------------------
        for i in range(dots_count):
            rect = QtCore.QRectF(x, y0, self._DOT_D, self._DOT_D)

            if i in local_breaks:
                base = (
                    self._break_color if i == current_dot else self._break_passed_color
                )
            elif i == current_dot:
                base = self._current_color
            elif i < passed_dots:
                base = self._passed_color
            else:
                base = self._empty_color

            if i in local_breaks and i == current_dot and self._flash_strength > 0.0:
                for factor in self._glow_layers:
                    glow_d = self._DOT_D + factor * 4
                    glow_rect = QtCore.QRectF(
                        rect.center().x() - glow_d / 2,
                        rect.center().y() - glow_d / 2,
                        glow_d,
                        glow_d,
                    )
                    glow_col = QtGui.QColor(self._break_color)
                    alpha = self._flash_strength * (0.4 / factor + 0.1)
                    glow_col.setAlpha(int(alpha * 255))
                    painter.setPen(QtCore.Qt.NoPen)
                    painter.setBrush(glow_col)
                    painter.drawEllipse(glow_rect)

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(base)
            painter.drawEllipse(rect)

            if i == dots_count - 1 and not has_chevron:
                glow_d = self._DOT_D + 4
                glow_rect = QtCore.QRectF(
                    rect.center().x() - glow_d / 2,
                    rect.center().y() - glow_d / 2,
                    glow_d,
                    glow_d,
                )
                glow_col = QtGui.QColor(self._current_color).lighter(130)
                glow_col.setAlpha(25)
                painter.setBrush(glow_col)
                painter.drawEllipse(glow_rect)

            x += self._DOT_D + self._DOT_SPC

        # Draw chevron ------------------------------------------------------
        if has_chevron:
            cw = self._DOT_D * self._chev_scale_w
            ch = self._DOT_D * self._chev_scale_h
            cx = x
            cy = y0 + (self._DOT_D - ch) / 2

            path = QtGui.QPainterPath()
            path.moveTo(cx, cy)
            path.lineTo(cx + cw, cy + ch / 2)
            path.moveTo(cx, cy + ch)
            path.lineTo(cx + cw, cy + ch / 2)

            core_col = self._chevron_color if chevron_filled else self._empty_color
            painter.setPen(
                QtGui.QPen(
                    core_col, self._chev_core_w, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap
                )
            )
            painter.drawPath(path)

            if self._flash_strength > 0.0:
                for factor in self._glow_layers:
                    pen = QtGui.QPen(
                        self._chevron_color,
                        self._chev_core_w * factor,
                        QtCore.Qt.SolidLine,
                        QtCore.Qt.RoundCap,
                    )
                    alpha = self._flash_strength * (0.4 / factor + 0.1)
                    glow_color = QtGui.QColor(self._chevron_color)
                    glow_color.setAlpha(int(alpha * 255))
                    pen.setColor(glow_color)
                    painter.setPen(pen)
                    painter.drawPath(path)
