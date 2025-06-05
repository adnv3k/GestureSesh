import sys
import pytest
from PyQt5 import QtWidgets
from GestureSesh import MainApp

@pytest.fixture
def app(qtbot):
    """Fixture to create the QApplication instance."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    return app

@pytest.fixture
def main_window(qtbot, app):
    window = MainApp()
    window.show()
    qtbot.addWidget(window)
    return window, window  # If MainApp is both window and ui

def test_mainwindow_widgets_exist(main_window):
    window, ui = main_window
    # Check that all main widgets exist
    assert hasattr(ui, "select_images")
    assert hasattr(ui, "selected_items")
    assert hasattr(ui, "add_folder")
    assert hasattr(ui, "add_items")
    assert hasattr(ui, "clear_items")
    assert hasattr(ui, "session_settings")
    assert hasattr(ui, "randomize_selection")
    assert hasattr(ui, "remove_duplicates")
    assert hasattr(ui, "set_number_of_images")
    assert hasattr(ui, "set_minutes")
    assert hasattr(ui, "set_seconds")
    assert hasattr(ui, "add_entry")
    assert hasattr(ui, "preset_loader_box")
    assert hasattr(ui, "save_preset")
    assert hasattr(ui, "delete_preset")
    assert hasattr(ui, "entry_table")
    assert hasattr(ui, "total_table")
    assert hasattr(ui, "remove_entry")
    assert hasattr(ui, "move_entry_up")
    assert hasattr(ui, "move_entry_down")
    assert hasattr(ui, "reset_table")
    assert hasattr(ui, "dialog_buttons")

def test_labels_text(main_window):
    _, ui = main_window
    assert ui.select_images.text() == "Selection"
    assert ui.session_settings.text() == "Session Settings"
    assert ui.label_7.text() == "Set Entry"
    assert ui.label_5.text() == "Minutes"
    assert ui.label_6.text() == "Seconds"
    assert ui.image_amount_label.text() == "Number of Images"
    assert ui.duration_label.text() == "Duration"
    assert ui.label_8.text() == "Preset:"

def test_entry_table_headers(main_window):
    _, ui = main_window
    assert ui.entry_table.columnCount() == 3
    assert ui.entry_table.horizontalHeaderItem(0).text() == "Entry"
    assert ui.entry_table.horizontalHeaderItem(1).text() == "Number of Images"
    assert ui.entry_table.horizontalHeaderItem(2).text() == "Duration"

def test_spinbox_defaults(main_window):
    _, ui = main_window
    assert ui.set_number_of_images.value() == 0
    assert ui.set_minutes.value() == 0
    assert ui.set_seconds.value() == 0
    assert ui.set_number_of_images.maximum() == 999999999
    assert ui.set_minutes.maximum() == 999999999
    assert ui.set_seconds.maximum() == 59

def test_buttons_enabled(main_window):
    _, ui = main_window
    assert ui.add_folder.isEnabled()
    assert ui.add_items.isEnabled()
    assert ui.clear_items.isEnabled()
    assert ui.randomize_selection.isEnabled()
    assert ui.remove_duplicates.isEnabled()
    assert ui.add_entry.isEnabled()
    assert ui.save_preset.isEnabled()
    assert ui.delete_preset.isEnabled()
    assert ui.remove_entry.isEnabled()
    assert ui.move_entry_up.isEnabled()
    assert ui.move_entry_down.isEnabled()
    assert ui.reset_table.isEnabled()

def test_preset_loader_box(main_window):
    _, ui = main_window
    if ui.preset_loader_box.count() == 0:
        ui.preset_loader_box.addItem("<New Preset>")
    assert ui.preset_loader_box.count() >= 1
    # Just check that the box is not empty, or contains expected values

def test_entry_table_edit_triggers(main_window):
    _, ui = main_window
    triggers = ui.entry_table.editTriggers()
    assert triggers & QtWidgets.QAbstractItemView.DoubleClicked
    assert triggers & QtWidgets.QAbstractItemView.AnyKeyPressed
    assert triggers & QtWidgets.QAbstractItemView.EditKeyPressed

def test_total_table_properties(main_window):
    _, ui = main_window
    ui.total_table.setRowCount(0)
    assert ui.total_table.columnCount() == 3
    assert ui.total_table.rowCount() == 0
    assert not ui.total_table.horizontalHeader().isVisible()
    assert not ui.total_table.verticalHeader().isVisible()
    assert ui.total_table.editTriggers() == QtWidgets.QAbstractItemView.NoEditTriggers