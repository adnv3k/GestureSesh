import sys
import pytest
from PyQt5 import QtWidgets, QtCore
from session_display import Ui_session_display

@pytest.fixture(scope="module")
def app():
    # Ensure a single QApplication instance for all tests
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    yield app

@pytest.fixture
def session_display_widget(app):
    # Create a QWidget and apply the UI
    widget = QtWidgets.QWidget()
    ui = Ui_session_display()
    ui.setupUi(widget)
    return widget, ui

def test_widget_object_names(session_display_widget):
    widget, ui = session_display_widget
    assert widget.objectName() == "session_display"
    assert ui.image_display.objectName() == "image_display"
    assert ui.session_info.objectName() == "session_info"
    assert ui.grayscale_button.objectName() == "grayscale_button"
    assert ui.flip_horizontal_button.objectName() == "flip_horizontal_button"
    assert ui.flip_vertical_button.objectName() == "flip_vertical_button"
    assert ui.previous_image.objectName() == "previous_image"
    assert ui.pause_timer.objectName() == "pause_timer"
    assert ui.stop_session.objectName() == "stop_session"
    assert ui.next_image.objectName() == "next_image"
    assert ui.timer_display.objectName() == "timer_display"

def test_session_info_label_properties(session_display_widget):
    _, ui = session_display_widget
    assert ui.session_info.maximumHeight() == 32
    assert ui.session_info.text() == "{session info}"
    assert ui.session_info.font().pointSize() == 15
    assert ui.session_info.font().bold()

def test_timer_display_label_properties(session_display_widget):
    _, ui = session_display_widget
    assert ui.timer_display.minimumWidth() == 61 or ui.timer_display.minimumSize().width() == 61
    assert ui.timer_display.text() == "00:00"
    assert ui.timer_display.font().bold()

def test_buttons_are_checkable(session_display_widget):
    _, ui = session_display_widget
    assert ui.grayscale_button.isCheckable()
    assert ui.flip_horizontal_button.isCheckable()
    assert ui.flip_vertical_button.isCheckable()
    assert not ui.previous_image.isCheckable()
    assert not ui.pause_timer.isCheckable()
    assert not ui.stop_session.isCheckable()
    assert not ui.next_image.isCheckable()

def test_tooltips_and_shortcuts(session_display_widget):
    _, ui = session_display_widget
    assert "Grayscale" in ui.grayscale_button.toolTip()
    assert ui.grayscale_button.shortcut().toString().upper() == "G"
    assert "Flip horizontal" in ui.flip_horizontal_button.toolTip()
    assert ui.flip_horizontal_button.shortcut().toString().upper() == "H"
    assert "Flip vertical" in ui.flip_vertical_button.toolTip()
    assert ui.flip_vertical_button.shortcut().toString().upper() == "V"
    assert "Previous image" in ui.previous_image.toolTip()
    assert ui.previous_image.shortcut().toString().upper() == "LEFT"
    assert "Pause Timer" in ui.pause_timer.toolTip()
    assert ui.pause_timer.shortcut().toString().upper() == "SPACE"
    assert "Stop Session" in ui.stop_session.toolTip()
    assert ui.stop_session.shortcut().toString().upper() == "ESC"
    assert "Next Image" in ui.next_image.toolTip()
    assert ui.next_image.shortcut().toString().upper() == "RIGHT"

def test_image_display_alignment_and_style(session_display_widget):
    _, ui = session_display_widget
    assert ui.image_display.alignment() == QtCore.Qt.AlignCenter
    assert "background: rgb(30,56,78);" in ui.image_display.styleSheet()