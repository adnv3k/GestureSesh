import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import io
import sys
import tempfile
import types
import unittest
from collections import OrderedDict
from unittest.mock import MagicMock

import numpy as np
from PIL import Image
from PyQt5.QtWidgets import QApplication

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from gesturesesh.session.image_loader import SessionImageLoaderMixin
from gesturesesh.session_window import SessionDisplay


class TestSessionImageLoaderMixin(unittest.TestCase):
    def test_prepare_image_mods_uses_animation_cache_and_starts_timer(self):
        frame = np.zeros((2, 2, 4), dtype=np.uint8)
        fake = types.SimpleNamespace(
            playlist=["animated.gif"],
            playlist_position=0,
            image_mods={"break": False},
            animation_cache=OrderedDict(),
            still_image_cache=OrderedDict(),
            max_animation_cache_entries=12,
            max_still_cache_entries=64,
            animation_timer=MagicMock(),
            animation_frames=[],
            animation_durations_ms=[],
            animation_frame_index=0,
            animation_source_path=None,
            reset_animation_state=MagicMock(),
            load_animation_frames=MagicMock(
                return_value=([frame, frame.copy()], [80, 90])
            ),
            _render_cvimage=MagicMock(),
        )
        fake._cache_get = lambda cache, key: SessionDisplay._cache_get(fake, cache, key)
        fake._cache_put = lambda cache, key, value, limit: SessionDisplay._cache_put(
            fake, cache, key, value, limit
        )

        SessionImageLoaderMixin.prepare_image_mods(fake)
        SessionImageLoaderMixin.prepare_image_mods(fake)

        fake.load_animation_frames.assert_called_once_with("animated.gif")
        assert fake.animation_source_path == "animated.gif"
        assert len(fake.animation_frames) == 2
        assert fake._render_cvimage.call_count == 2
        fake.animation_timer.start.assert_called_with(80)

    def test_prepare_image_mods_falls_back_to_still_cache(self):
        image = np.ones((2, 2, 3), dtype=np.uint8)
        fake = types.SimpleNamespace(
            playlist=["still.jpg"],
            playlist_position=0,
            image_mods={"break": False},
            animation_cache=OrderedDict(),
            still_image_cache=OrderedDict(),
            max_animation_cache_entries=12,
            max_still_cache_entries=64,
            reset_animation_state=MagicMock(),
            load_animation_frames=MagicMock(return_value=None),
            decode_current_image=MagicMock(return_value=image),
            _render_cvimage=MagicMock(),
        )
        fake._cache_get = lambda cache, key: SessionDisplay._cache_get(fake, cache, key)
        fake._cache_put = lambda cache, key, value, limit: SessionDisplay._cache_put(
            fake, cache, key, value, limit
        )

        SessionImageLoaderMixin.prepare_image_mods(fake)
        SessionImageLoaderMixin.prepare_image_mods(fake)

        fake.decode_current_image.assert_called_once()
        assert fake._render_cvimage.call_count == 2

    def test_normalize_cvimage_dtype_scales_common_image_depths(self):
        fake = types.SimpleNamespace()

        bool_image = np.array([[True, False]])
        uint16_image = np.array([[0, 1023]], dtype=np.uint16)
        float_image = np.array([[0.0, 1.0]], dtype=np.float32)

        assert SessionImageLoaderMixin.normalize_cvimage_dtype(
            fake, bool_image
        ).tolist() == [[255, 0]]
        assert SessionImageLoaderMixin.normalize_cvimage_dtype(
            fake, uint16_image
        ).tolist() == [[0, 255]]
        assert SessionImageLoaderMixin.normalize_cvimage_dtype(
            fake, float_image
        ).tolist() == [[0, 255]]


class TestExifOrientation(unittest.TestCase):
    """``IMREAD_UNCHANGED`` ignores EXIF orientation, so decode_with_cv2 must
    re-apply it (regression from the 0.5.x image-loading refactor)."""

    @staticmethod
    def _decoder_fake():
        fake = types.SimpleNamespace()
        fake._apply_exif_orientation = (
            lambda cvimage, path: SessionImageLoaderMixin._apply_exif_orientation(
                fake, cvimage, path
            )
        )
        return fake

    @staticmethod
    def _write_jpeg(path, height, width, orientation):
        # A distinctive bright patch in the top-left so we can confirm not just
        # the shape swap but the rotation direction.
        arr = np.full((height, width, 3), 30, dtype=np.uint8)
        arr[0 : height // 2, 0 : width // 2] = (255, 0, 0)
        image = Image.fromarray(arr)
        exif = image.getexif()
        exif[0x0112] = orientation
        image.save(path, format="JPEG", quality=95, exif=exif)

    def test_decode_with_cv2_rotates_per_orientation_tag(self):
        fake = self._decoder_fake()
        with tempfile.TemporaryDirectory() as tmp:
            # Stored pixels are landscape 20x40 (H x W).
            for orientation, expect_swap in ((1, False), (6, True), (8, True)):
                path = os.path.join(tmp, f"o{orientation}.jpg")
                self._write_jpeg(path, height=20, width=40, orientation=orientation)
                out = SessionImageLoaderMixin.decode_with_cv2(fake, path)
                self.assertIsNotNone(out)
                h, w = out.shape[:2]
                if expect_swap:
                    self.assertEqual((h, w), (40, 20), f"orientation {orientation}")
                else:
                    self.assertEqual((h, w), (20, 40), f"orientation {orientation}")

    def test_orientation_6_and_8_rotate_opposite_directions(self):
        fake = self._decoder_fake()
        with tempfile.TemporaryDirectory() as tmp:
            p6 = os.path.join(tmp, "o6.jpg")
            p8 = os.path.join(tmp, "o8.jpg")
            self._write_jpeg(p6, height=20, width=40, orientation=6)
            self._write_jpeg(p8, height=20, width=40, orientation=8)
            out6 = SessionImageLoaderMixin.decode_with_cv2(fake, p6)
            out8 = SessionImageLoaderMixin.decode_with_cv2(fake, p8)
            # Both become portrait but the red patch lands in opposite corners:
            # orientation 6 (90 CW) -> top-right; orientation 8 (90 CCW) -> bottom-left.
            def is_red(px):
                b, g, r = int(px[0]), int(px[1]), int(px[2])
                return r > 150 and g < 80 and b < 80
            self.assertTrue(is_red(out6[2, -2]))   # top-right
            self.assertTrue(is_red(out8[-3, 1]))   # bottom-left

    def test_apply_exif_orientation_is_a_noop_without_metadata(self):
        fake = self._decoder_fake()
        cvimage = np.zeros((4, 6, 3), dtype=np.uint8)
        # Resource paths (the break image) and missing Pillow metadata are left
        # untouched rather than raising.
        self.assertIs(
            SessionImageLoaderMixin._apply_exif_orientation(
                fake, cvimage, ":/break/break.png"
            ),
            cvimage,
        )
        self.assertIsNone(
            SessionImageLoaderMixin._apply_exif_orientation(fake, None, "missing.jpg")
        )
