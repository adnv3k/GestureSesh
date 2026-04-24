"""Shared data models for the main application window."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5 import QtCore


@dataclass
class ScheduleEntry:
    images: int
    time: int


@dataclass
class StatusMessage:
    text: str
    duration: int  # milliseconds
    is_error: bool = False
    allow_rich_text: bool = False
    timer: QtCore.QTimer | None = None
    blink_timer: QtCore.QTimer | None = None
    fade_timer: QtCore.QTimer | None = None
    is_blinking: bool = False
    fade_step: int = 0
    _blink_cycle_count: int = 0
    _current_fade_step: int = 0
    _fade_direction: str = "out"
    _max_blink_cycles: int = 0
    _fade_steps: int = 0
    _is_fading_out: bool = False
