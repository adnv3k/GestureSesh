import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import types
import unittest
from collections import OrderedDict
from unittest.mock import MagicMock

import numpy as np
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
