"""Per-image timer, countdown, audio cues, and review-mode close countdown."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui
from PyQt5.QtTest import QTest
from pygame import mixer

from gesturesesh.session.constants import BREAK_IMAGE_PATH, sound_file


class SessionTimerMixin:
    """Timer/countdown behavior mixed into ``SessionDisplay``."""

    PAUSE_BUTTON_RUNNING_STYLE = (
        "background: rgb(100, 120, 118); padding:2px; border:1px solid transparent;"
    )
    PAUSE_BUTTON_PAUSED_STYLE = (
        "background: rgb(100, 120, 118); padding:2px; border:1px solid white;"
    )
    TIMER_DISPLAY_RUNNING_STYLE = "color: white;"
    TIMER_DISPLAY_PAUSED_STYLE = "color: white; border:1px solid white;"

    def init_timer(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.countdown)
        self.timer.start(500)
        self.session_finished = False
        self.close_seconds = 15
        self.close_timer = QtCore.QTimer()
        self.close_timer.timeout.connect(self.close_countdown)
        self.sec = ["0", "0"]
        self.minutes_list = ["0", "0"]
        self.hrs_list = ["0", "0"]

    def format_seconds(self, sec):
        minutes = int(sec / 60)
        sec = int(self.time_seconds - (minutes * 60))
        return f"{minutes}:{sec}"

    def countdown(self):
        self.update_timer_display()
        self._update_predictive_indicator_cues()
        if self.entry["time"] >= 30:
            if self.time_seconds == self.entry["time"] // 2:
                with sound_file("halfway.mp3") as p:
                    mixer.music.load(str(p))
                mixer.music.play()
        if self.time_seconds <= 10:
            if self.new_entry is False and self.end_of_entry is False:
                if self.time_seconds == 10:
                    with sound_file("first_alert.mp3") as p:
                        mixer.music.load(str(p))
                    mixer.music.play()
                elif self.time_seconds == 5:
                    with sound_file("second_alert.mp3") as p:
                        mixer.music.load(str(p))
                    mixer.music.play()
                elif self.time_seconds == 0.5:
                    with sound_file("third_alert.mp3") as p:
                        mixer.music.load(str(p))
                    mixer.music.play()
            else:
                if self.new_entry is True:
                    self.new_entry = False
                if self.end_of_entry is True:
                    self.end_of_entry = False
            if self.playlist[self.playlist_position] == BREAK_IMAGE_PATH:
                self.image_mods["break_grayscale"] = False
                self.prepare_image_mods()
        if self.time_seconds == 0:
            QTest.qWait(500)
            self.load_next_image()
            return
        self.time_seconds -= 0.5

    def update_timer_display(self):
        hr = int(self.time_seconds / 3600)
        self.hrs_list = list(str(hr))
        if len(self.hrs_list) == 1 or self.hrs_list[0] == "0":
            self.hrs_list.insert(0, "0")

        minutes = int((self.time_seconds / 3600 - hr) * 60)
        self.minutes_list = list(str(minutes))
        if len(self.minutes_list) == 1 or self.minutes_list[0] == "0":
            self.minutes_list.insert(0, "0")
        self.sec = list(
            str(int((((self.time_seconds / 3600 - hr) * 60) - minutes) * 60))
        )
        if len(self.sec) == 1 or self.sec[0] == "0":
            self.sec.insert(0, "0")
        self.display_time()

    def _set_timer_visuals(self, running: bool) -> None:
        """Update pause button and display border based on running state."""
        if running:
            self.pause_timer.setIcon(QtGui.QIcon(":/icons/icons/Pause.png"))
            self.pause_timer.setStyleSheet(self.PAUSE_BUTTON_RUNNING_STYLE)
            self.timer_display.setStyleSheet(self.TIMER_DISPLAY_RUNNING_STYLE)
        else:
            self.pause_timer.setIcon(QtGui.QIcon(":/icons/icons/Play2.png"))
            self.pause_timer.setStyleSheet(self.PAUSE_BUTTON_PAUSED_STYLE)
            self.timer_display.setStyleSheet(self.TIMER_DISPLAY_PAUSED_STYLE)

    def pause(self):
        if self.session_finished:
            return
        self.update_timer_display()
        if self.timer.isActive():
            self.timer.stop()
            self._set_timer_visuals(False)
        else:
            self._set_timer_visuals(True)
            self.timer.start(500)
        self.display_time()

    def display_time(self):
        """Displays amount of time left depending on how many seconds are left."""
        if self.time_seconds >= 3600:
            self.timer_display.setText(
                f"{self.hrs_list[0]}{self.hrs_list[1]}:"
                f"{self.minutes_list[0]}{self.minutes_list[1]}:"
                f"{self.sec[0]}{self.sec[1]}"
            )
        elif self.time_seconds >= 60:
            self.timer_display.setText(
                f"{self.minutes_list[0]}{self.minutes_list[1]}:"
                f"{self.sec[0]}{self.sec[1]}"
            )
        else:
            self.timer_display.setText(f"{self.sec[0]}{self.sec[1]}")

    def add_30_seconds(self):
        if self.session_finished:
            return
        self.time_seconds += 30
        self.update_timer_display()

    def add_60_seconds(self):
        if self.session_finished:
            return
        self.time_seconds += 60
        self.update_timer_display()

    def restart_timer(self):
        if self.session_finished:
            return
        self.time_seconds = self.schedule[self.entry["current"]].time

    def update_close_title(self):
        self.setWindowTitle(
            f"Review mode - closing in {self.close_seconds}s (Ctrl+O opens folder)"
        )

    def close_countdown(self):
        if not self.close_timer.isActive():
            return
        self.close_seconds -= 1
        if self.close_seconds <= 0:
            self.close_timer.stop()
            self.close()
            return
        self.timer_display.setText(f"Done! Closing in {self.close_seconds}s...")
        self.update_close_title()

    def cancel_close_countdown(self):
        if self.close_timer.isActive():
            self.close_timer.stop()
            self.timer_display.setText("Done!")
            self.setWindowTitle("Session complete - review mode (Ctrl+O opens folder)")
