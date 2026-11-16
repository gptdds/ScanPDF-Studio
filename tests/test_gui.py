import os

import pytest


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_and_navigation(qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("SCANPDF_DATA_DIR", str(tmp_path))
    from scanpdf.app.window import MainWindow
    window = MainWindow()
    assert window.stack.currentWidget() is window.home
    window.navigate("settings")
    assert window.stack.currentWidget() is window.preferences
    window.preferences.save()
    window.navigate("history")
    assert window.stack.currentWidget() is window.history_page
    window.close()

