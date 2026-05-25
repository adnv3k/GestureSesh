"""Image decoding, animation frame loading, and render preparation."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PyQt5 import QtCore, QtGui

try:
    from PIL import Image, ImageOps, ImageSequence
except ImportError:
    Image = None
    ImageOps = None
    ImageSequence = None

# Registers the JPEG XL codec with Pillow on import. Pillow has no built-in
# JXL support, so without this plugin .jxl files cannot be decoded.
try:
    import pillow_jxl  # noqa: F401
except ImportError:
    pass

from gesturesesh.session.constants import SUPPORTED_ANIMATED_TYPES


class SessionImageLoaderMixin:
    """Decode still/animated images and render them into the session display."""

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
                    frame_duration = int(
                        pil_image.info.get("duration", base_duration) or 100
                    )
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
                [
                    ffmpeg_path,
                    "-v",
                    "error",
                    "-i",
                    image_path,
                    "-vsync",
                    "0",
                    frame_pattern,
                ],
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
            if resized_pixmap is not None and not resized_pixmap.isNull():
                scaled_size = self.scaling_size.scaled(
                    resized_pixmap.size(), QtCore.Qt.KeepAspectRatio
                )
                self.scaling_size = QtCore.QSize(scaled_size)

        scaled_for_resize = self.image.scaled(
            self.scaling_size,
            aspectRatioMode=QtCore.Qt.KeepAspectRatioByExpanding,
            transformMode=QtCore.Qt.SmoothTransformation,
        )

        if getattr(self, "_fullscreen_frameless", False):
            self.image_scaled = scaled_for_resize
        else:
            self.image_scaled = None

        self.update_image_view()
        self.image_display.resize(scaled_for_resize.size())
        controls_height = self._controls_row_height()
        self.resize(
            scaled_for_resize.size().width(),
            scaled_for_resize.size().height() + controls_height,
        )
        self.previous_size = self.size()

    def decode_current_image(self):
        image_path = self.playlist[self.playlist_position]

        # cv2 handles common formats; Pillow covers AVIF/WEBP/JXL (the latter
        # via pillow-jxl-plugin); djxl is a last-resort fallback for JXL.
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
