"""Keyboard shortcut registration for SessionDisplay."""

from __future__ import annotations

from PyQt5 import QtGui
from PyQt5.QtWidgets import QShortcut


class SessionShortcutsMixin:
    """Registers all keyboard shortcuts and builds the shortcut-map data.

    Mixed into ``SessionDisplay``. Populates ``self.shortcut_map_rows`` for
    the F1/Ctrl+/ help dialog.
    """

    def init_shortcuts(self):
        self.shortcut_map_rows = []

        def register_shortcut(sequence, callback, action, details, group):
            shortcut = QShortcut(QtGui.QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self.shortcut_map_rows.append((group, sequence, action, details))
            return shortcut

        self.toggle_resize_key = register_shortcut(
            "R",
            self.toggle_resize,
            "Toggle resize mode",
            "Switch between fit-inside and fill-window display behavior.",
            "Window & View",
        )
        self.always_on_top_key = register_shortcut(
            "A",
            self.toggle_always_on_top,
            "Toggle always-on-top",
            "Keep the slideshow window above other windows.",
            "Window & View",
        )
        self.mute_key = register_shortcut(
            "M",
            self.toggle_mute,
            "Toggle mute",
            "Mute/unmute session sound cues.",
            "Audio & Timing",
        )
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
        self.skip_image_key = register_shortcut(
            "S",
            self.skip_image,
            "Skip image",
            "Swap current image forward with a later image in the session.",
            "Navigation",
        )
        self.frameless_window = register_shortcut(
            "Ctrl+F",
            self.toggle_frameless,
            "Toggle frameless window",
            "Hide/show window frame.",
            "Window & View",
        )
        self.frameless_fullscreen = register_shortcut(
            "Ctrl+Shift+F",
            self.toggle_fullscreen_frameless,
            "Toggle frameless fullscreen",
            "Enter/exit frameless fullscreen with no OS chrome.",
            "Window & View",
        )
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
        self.grayscale_shortcut = register_shortcut(
            "G",
            self.grayscale,
            "Toggle grayscale",
            "Enable or disable grayscale for the current image.",
            "Image Filters",
        )
        self.flip_horizontal_shortcut = register_shortcut(
            "H",
            self.flip_horizontal,
            "Flip horizontal",
            "Mirror the current image horizontally.",
            "Image Filters",
        )
        self.flip_vertical_shortcut = register_shortcut(
            "V",
            self.flip_vertical,
            "Flip vertical",
            "Mirror the current image vertically.",
            "Image Filters",
        )
        self.open_directory_key = register_shortcut(
            "Ctrl+O",
            self.open_image_directory,
            "Open image folder",
            "Open the folder containing the current image.",
            "Navigation",
        )
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
            "Show the keyboard shortcut legend for the session window.",
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
