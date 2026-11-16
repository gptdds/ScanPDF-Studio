import os
import sys

from scanpdf.services.paths import bundled_root


def main():
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication

    from scanpdf.app.window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("ScanPDF Studio")
    app.setOrganizationName("ScanPDF Studio")
    app.setApplicationVersion("0.1.0")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    icon = bundled_root() / "resources" / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

