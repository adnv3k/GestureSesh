#!/usr/bin/env python3
"""Headless smoke test for GestureSesh GUI flows.

This script instantiates `MainApp` headlessly (offscreen) and exercises
several code paths: preset save/load, status messages, directory scanning,
remove duplicates, randomization, `DotIndicator` pulses, and a mocked
`SessionDisplay` start.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import tempfile
import shutil

from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest

# Make local src importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

os.chdir(ROOT)


def main():
    app = QApplication(['smoke'])
    import importlib
    gm = importlib.import_module('gesturesesh.main')

    # Replace the real SessionDisplay with a lightweight mock to avoid GUI
    class MockDisplay:
        def __init__(self, schedule=None, items=None, total=None):
            class _Closed:
                def connect(self, fn):
                    return None

            self.closed = _Closed()

        def show(self):
            return None

    gm.SessionDisplay = MockDisplay

    view = gm.MainApp()

    results = []
    tmp = None
    try:
        # 1) Append a schedule entry and verify
        view.set_number_of_images.setValue(1)
        view.set_minutes.setValue(0)
        view.set_seconds.setValue(1)
        view.append_schedule()
        results.append(('append_schedule_rows', view.entry_table.rowCount()))

        # 2) Save and load preset
        name = 'smoke_preset'
        try:
            view.preset_loader_box.addItem(name)
            view.preset_loader_box.setCurrentText(name)
        except Exception:
            # Some Qt versions don't support setCurrentText; set index instead
            view.preset_loader_box.setCurrentIndex(view.preset_loader_box.count() - 1)
        view.save()
        results.append(('preset_saved', name in view.presets))
        view.load()
        results.append(('preset_loaded_rows', view.entry_table.rowCount()))

        # 3) Status messages & blink animation triggers
        for i in range(4):
            view.show_temporary_status(f"smoke {i}", 300, is_error=(i % 2 == 0))
            QTest.qWait(50)
        QTest.qWait(800)
        results.append(('status_messages_displayed', True))

        # 4) Scan directories with temporary files
        tmp = tempfile.mkdtemp()
        f1 = os.path.join(tmp, 'img1.jpg')
        f2 = os.path.join(tmp, 'img2.png')
        with open(f1, 'w') as fh:
            fh.write('x')
        with open(f2, 'w') as fh:
            fh.write('y')
        view.valid_file_types = {'.jpg', '.png', '.jpeg', '.bmp'}
        view.selection = {'folders': [], 'files': []}
        valid, invalid = view.scan_directories([tmp])
        results.append(('scan_dirs', valid, invalid))

        # 5) Remove duplicates + randomize
        view.selection['files'] = [f1, f1, f2]
        view.remove_dupes()
        results.append(('remove_dupes_len', len(view.selection['files'])))
        view.selection['files'] = [f1, f2, f1, f2]
        view.randomize_items()
        results.append(('randomize_len', len(view.selection['files'])))

        # 6) DotIndicator triggers
        from gesturesesh.ui.dot_indicator import DotIndicator

        dot = DotIndicator(parent=view)
        dot.setMaximum(5)
        dot.setValue(1)
        dot.trigger_focus_flash()
        QTest.qWait(150)
        dot.trigger_soft_pulse()
        QTest.qWait(150)
        dot.trigger_milestone_pulse()
        QTest.qWait(150)
        results.append(('dot_triggers', True))

        # 7) Start session (uses MockDisplay)
        view.grab_schedule()
        if not view.selection['files']:
            view.selection['files'] = [f1]
        # Ensure totals are set
        if not view.session_schedule:
            view.session_schedule = [gm.ScheduleEntry(1, 1)]
        view.total_scheduled_images = sum(e.images for e in view.session_schedule)
        view.start_session()
        QTest.qWait(100)
        results.append(('start_session', True))

    except Exception as exc:
        import traceback

        traceback.print_exc()
        results.append(('exception', str(exc)))
    finally:
        if tmp and os.path.isdir(tmp):
            try:
                shutil.rmtree(tmp)
            except Exception:
                pass
        try:
            view.close()
        except Exception:
            pass
        app.quit()

    print('SMOKE_RESULTS', results)


if __name__ == '__main__':
    main()
