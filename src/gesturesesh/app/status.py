"""Status queue and animation behavior for the main window."""

from __future__ import annotations

from PyQt5 import QtCore

from gesturesesh.app.models import StatusMessage


class MainAppStatusMixin:
    """Status-rendering behavior mixed into ``MainApp``."""

    def display_status(self):
        """Displays amount of files, and folders selected"""
        default_message = (
            f'{len(self.selection["files"])} total files added from '
            f'{len(self.selection["folders"])} folder(s).'
        )

        if not self.status_messages:
            if (
                self.showing_default_status
                and self.selected_items.toPlainText() == default_message
            ):
                return

            self.status_opacity_effect.setOpacity(0.8)
            self.selected_items.setHtml(f"<div>{default_message}</div>")
            self.showing_default_status = True

    def show_temporary_status(self, message, duration_ms=2000, is_error=False):
        """Shows a temporary status message with sophisticated animations"""
        self._add_status_message(message, duration_ms, is_error)

    def show_error_status(self, message, duration_ms=3000):
        """Shows an error/warning status message with faster, more attention-grabbing animations"""
        self._add_status_message(message, duration_ms, is_error=True)

    def _remove_status_message(self, status_msg):
        """Start fade-out animation and remove a status message after its timer expires."""
        if getattr(status_msg, "_is_fading_out", False):
            return

        status_msg._is_fading_out = True

        status_msg.timer.stop()
        status_msg.timer.deleteLater()

        self._fade_out_and_remove(status_msg)

    def _fade_out_and_remove(self, status_msg):
        """Fade a status message out smoothly, then remove it from the queue."""
        fade_steps = 20
        fade_duration = 400
        start_opacity = 0.6
        step_duration = fade_duration // fade_steps

        status_msg._fade_step = 0

        fade_timer = QtCore.QTimer()
        fade_timer.setSingleShot(False)

        def _step():
            progress = status_msg._fade_step / fade_steps
            opacity = start_opacity * (1 - progress)
            self._update_display_with_selective_opacity(status_msg, opacity)

            status_msg._fade_step += 1
            if status_msg._fade_step > fade_steps:
                fade_timer.stop()
                fade_timer.deleteLater()
                if status_msg in self.status_messages:
                    self.status_messages.remove(status_msg)
                self._update_status_display()

        fade_timer.timeout.connect(_step)
        fade_timer.start(step_duration)
        status_msg._fade_timer = fade_timer

    def _add_status_message(self, message, duration_ms, is_error=False):
        """Add a new status message to the queue and display it"""
        message_timer = QtCore.QTimer()
        message_timer.setSingleShot(True)

        status_msg = StatusMessage(message, duration_ms, is_error)
        status_msg.timer = message_timer

        message_timer.timeout.connect(lambda: self._remove_status_message(status_msg))

        for existing_msg in self.status_messages:
            try:
                existing_msg.is_blinking = False
            except Exception as e:
                print(f"Exception while setting is_blinking: {e}")
                pass
            try:
                blink_timer = getattr(existing_msg, "blink_timer", None)
                if blink_timer is not None:
                    try:
                        blink_timer.stop()
                    except Exception as e:
                        print(f"Exception while stopping blink timer: {e}")
            except Exception as e:
                print(f"Exception while stopping blink timer: {e}")
                pass

        self.status_messages.append(status_msg)

        self._update_status_display_text()

        self._start_message_blink_animation(status_msg, is_error)

        message_timer.start(7000)

    def _debounced_update_status_display(self):
        """Debounce status display updates to prevent UI freezing"""
        self.status_update_timer.start(50)

    def _update_status_display(self):
        """Update the status display with current messages"""
        if self.status_messages:
            self._debounced_update_status_display()
        else:
            self.display_status()

    def _start_message_blink_animation(self, status_msg, is_error=False):
        """Start blinking animation for a specific message"""
        status_msg.is_blinking = True

        max_blink_cycles = 3 if is_error else 2
        fade_duration = 300 if is_error else 400
        fade_steps = 20
        fade_step_duration = fade_duration // fade_steps

        status_msg._blink_cycle_count = 0
        status_msg._current_fade_step = 0
        status_msg._fade_direction = "out"
        status_msg._max_blink_cycles = max_blink_cycles
        status_msg._fade_steps = fade_steps

        blink_timer = QtCore.QTimer()
        blink_timer.setSingleShot(False)

        status_msg.blink_timer = blink_timer

        def animate_message_fade():
            if not status_msg.is_blinking or status_msg not in self.status_messages:
                blink_timer.stop()
                blink_timer.deleteLater()
                return

            if status_msg._fade_direction == "out":
                progress = status_msg._current_fade_step / status_msg._fade_steps
                current_opacity = 1.0 - (0.8 * progress)
            else:
                progress = status_msg._current_fade_step / status_msg._fade_steps
                current_opacity = 0.2 + (0.8 * progress)

            self._update_display_with_selective_opacity(status_msg, current_opacity)

            status_msg._current_fade_step += 1

            if status_msg._current_fade_step >= status_msg._fade_steps:
                if status_msg._fade_direction == "out":
                    status_msg._fade_direction = "in"
                    status_msg._current_fade_step = 0
                else:
                    status_msg._blink_cycle_count += 1

                    if status_msg._blink_cycle_count < status_msg._max_blink_cycles:
                        blink_timer.stop()

                        def restart_cycle():
                            if (
                                status_msg.is_blinking
                                and status_msg in self.status_messages
                            ):
                                status_msg._current_fade_step = 0
                                status_msg._fade_direction = "out"
                                blink_timer.start(fade_step_duration)

                        QtCore.QTimer.singleShot(200, restart_cycle)
                        return
                    else:
                        self._finish_message_blink_animation(status_msg)
                        blink_timer.stop()
                        blink_timer.deleteLater()
                        return

        blink_timer.timeout.connect(animate_message_fade)
        blink_timer.start(fade_step_duration)

    def _finish_message_blink_animation(self, status_msg):
        """Restore normal state for a specific message after blinking completes"""
        status_msg.is_blinking = False
        try:
            bt = getattr(status_msg, "blink_timer", None)
            if bt is not None:
                try:
                    bt.stop()
                except Exception as e:
                    print(f"Exception while finishing blink timer: {e}")
                try:
                    bt.deleteLater()
                except Exception:
                    pass
                status_msg.blink_timer = None
        except Exception:
            pass

        self.status_opacity_effect.setOpacity(1.0)

        self._update_status_display_text()

    def _render_status(
        self, highlight: StatusMessage | None = None, opacity: float | None = None
    ) -> None:
        """
        Draw all status messages. If *highlight* is supplied, that message is
        rendered in the given *opacity* (0-1). All others use full colour.
        """
        if not self.status_messages:
            self.display_status()
            return

        self.status_opacity_effect.setOpacity(1.0)

        html = ['<div style="line-height:1.1;">']
        visible = list(reversed(self.status_messages))
        for i, msg in enumerate(visible):
            margin = "margin-top:3px;" if i else ""

            if msg is highlight:
                base_rgb = "220, 20, 60" if msg.is_error else "225, 225, 225"
                css = f"font-weight:bold; color:rgba({base_rgb}, {opacity}); {margin}"
            elif i == 0:
                css = (
                    "font-weight:bold;"
                    f' {"color:#DC143C;" if msg.is_error else ""} {margin}'
                )
            else:
                css = f"color:rgb(102,102,102); {margin}"

            html.append(f'<div style="{css}">{msg.text}</div>')
        html.append("</div>")

        self.selected_items.setHtml("".join(html))
        self.showing_default_status = False

    def _update_display_with_selective_opacity(self, blinking_msg, opacity):
        self._render_status(blinking_msg, opacity)

    def _update_status_display_text(self):
        self._render_status()

    def display_random_status(self):
        """Displays the randomization setting"""
        if self.randomize_selection.isChecked():
            self.show_temporary_status("Randomization on!", 2000)
        else:
            self.show_temporary_status("Randomization off!", 2000)
