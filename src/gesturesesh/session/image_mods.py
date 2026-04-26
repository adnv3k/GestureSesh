"""Image modification state and operations for SessionDisplay.

Owns the ``image_mods`` dict and all toggle/adjust actions for grayscale,
flips, brightness/contrast, threshold, and edge filters. Also provides the
shared CV2 modifier pipeline used during render.
"""

from __future__ import annotations

import cv2
import numpy as np


class SessionImageModsMixin:
    """Image-modification behavior mixed into ``SessionDisplay``."""

    def init_image_mods(self):
        self.image_mods = {
            "break": False,
            "grayscale": False,
            "hflip": False,
            "vflip": False,
            "break_grayscale": False,
            "brightness": 0,
            "contrast": 1.0,
            "threshold": False,
            "edge": False,
            "grayscale_mode": "perceptual",  # or "simple"
        }

    def reset_image_mods(self):
        """Reset all image modifications to their default values and update the display."""
        self.init_image_mods()
        self.display_image(play_sound=False)

    def _apply_modifiers_to_cvimage(self, cvimage):
        cvimage = cvimage.copy()
        b = self.image_mods["brightness"]
        c = self.image_mods["contrast"]
        if b != 0 or c != 1.0:
            cvimage = cv2.convertScaleAbs(cvimage, alpha=c, beta=b)

        grayscale_active = (
            self.image_mods["grayscale"] or self.image_mods["break_grayscale"]
        )
        if grayscale_active or self.image_mods["threshold"] or self.image_mods["edge"]:
            if self.image_mods.get("grayscale_mode", "perceptual") == "simple":
                gray = self.to_simple_grayscale(cvimage)
            else:
                gray = self.to_fidelous_grayscale(cvimage)
            if gray.ndim == 3 and gray.shape[2] == 4:
                gray_for_binary = cv2.cvtColor(gray, cv2.COLOR_BGRA2GRAY)
            elif gray.ndim == 3 and gray.shape[2] == 3:
                gray_for_binary = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
            else:
                gray_for_binary = gray

            if grayscale_active:
                cvimage = gray
            if self.image_mods["threshold"]:
                _, cvimage = cv2.threshold(
                    gray_for_binary, 1286, 255, cv2.THRESH_BINARY
                )
            if self.image_mods["edge"]:
                cvimage = cv2.Canny(gray_for_binary, 100, 200)

        if self.image_mods["hflip"]:
            cvimage = cv2.flip(cvimage, 1)
        if self.image_mods["vflip"]:
            cvimage = cv2.flip(cvimage, 0)
        return cvimage

    def to_fidelous_grayscale(self, image):
        if image.ndim == 3 and image.shape[2] == 4:
            b, g, r, a = cv2.split(image)
            rgb = cv2.merge([r, g, b]).astype(np.float32)
            gray = np.dot(rgb, [0.2126, 0.7152, 0.0722])
            gray = np.clip(gray, 0, 255).astype(np.uint8)
            result = cv2.merge([gray, gray, gray, a])
            return result
        else:
            rgb = image[..., ::-1].astype(np.float32)
            gray = np.dot(rgb, [0.2126, 0.7152, 0.0722])
            gray = np.clip(gray, 0, 255).astype(np.uint8)
            return gray

    def to_simple_grayscale(self, image):
        """Simple grayscale: convert BGR image to single channel grayscale."""
        if image.ndim == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def toggle_grayscale_mode(self):
        """Toggle between perceptual and simple grayscale modes."""
        if self.image_mods["grayscale_mode"] == "perceptual":
            self.image_mods["grayscale_mode"] = "simple"
            self.setWindowTitle("Simple Grayscale Mode")
        else:
            self.image_mods["grayscale_mode"] = "perceptual"
            self.setWindowTitle("Perceptual Grayscale Mode")
        self.display_image(play_sound=False)

    def flip_horizontal(self):
        self.image_mods["hflip"] = not self.image_mods["hflip"]
        self.display_image(play_sound=False)

    def flip_vertical(self):
        self.image_mods["vflip"] = not self.image_mods["vflip"]
        self.display_image(play_sound=False)

    def grayscale(self):
        self.image_mods["grayscale"] = not self.image_mods["grayscale"]
        self.display_image(play_sound=False)

    def increase_brightness(self):
        self.image_mods["brightness"] = min(self.image_mods["brightness"] + 10, 100)
        self.display_image()

    def decrease_brightness(self):
        self.image_mods["brightness"] = max(self.image_mods["brightness"] - 10, -100)
        self.display_image()

    def increase_contrast(self):
        self.image_mods["contrast"] = min(self.image_mods["contrast"] + 0.1, 3.0)
        self.display_image()

    def decrease_contrast(self):
        self.image_mods["contrast"] = max(self.image_mods["contrast"] - 0.1, 0.1)
        self.display_image()

    def toggle_threshold(self):
        self.image_mods["threshold"] = not self.image_mods["threshold"]
        self.display_image()

    def toggle_edge(self):
        self.image_mods["edge"] = not self.image_mods["edge"]
        self.display_image()
