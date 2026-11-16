from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout,
                               QWidget)


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")


class PageImage(QWidget):
    clicked = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap()
        self.blocks = []
        self.selected = None
        self.scale = 1.0
        self.offset = QPoint(0, 0)
        self.setMinimumSize(360, 480)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def load(self, path):
        self.pixmap = QPixmap(str(path))
        self.blocks = []
        self.selected = None
        self.update()

    def set_blocks(self, blocks):
        self.blocks = blocks
        self.update()

    def select(self, block_id):
        self.selected = block_id
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#262b2e"))
        if self.pixmap.isNull():
            painter.setPen(QColor("#aeb7bb"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "页面预览")
            return
        margin = 18
        available_width = self.width() - margin * 2
        available_height = self.height() - margin * 2
        self.scale = min(available_width / self.pixmap.width(),
                         available_height / self.pixmap.height())
        width = int(self.pixmap.width() * self.scale)
        height = int(self.pixmap.height() * self.scale)
        self.offset = QPoint((self.width() - width) // 2, (self.height() - height) // 2)
        target = QRectF(self.offset.x(), self.offset.y(), width, height)
        painter.drawPixmap(target.toRect(), self.pixmap)
        for block in self.blocks:
            left, top, right, bottom = block.rect
            rect = QRectF(self.offset.x() + left * self.scale, self.offset.y() + top * self.scale,
                          (right - left) * self.scale, (bottom - top) * self.scale)
            active = block.id == self.selected
            color = QColor("#f1a33c") if block.confidence < 0.85 else QColor("#4f9b8b")
            if active:
                color = QColor("#e45c45")
            pen = QPen(color, 2.2 if active else 1.2)
            if not active:
                fill = QColor(color)
                fill.setAlpha(26)
                painter.fillRect(rect, fill)
            painter.setPen(pen)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if self.pixmap.isNull():
            return
        x = (event.position().x() - self.offset.x()) / self.scale
        y = (event.position().y() - self.offset.y()) / self.scale
        candidates = [block for block in self.blocks
                      if block.rect[0] <= x <= block.rect[2] and block.rect[1] <= y <= block.rect[3]]
        if candidates:
            block = min(candidates, key=lambda item: item.height)
            self.selected = block.id
            self.update()
        self.clicked.emit(x, y)


class ImageViewer(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_image = PageImage()
        self.setWidget(self.page_image)
        self.setWidgetResizable(True)
        self.page_image.setMinimumSize(300, 400)

    def load(self, path):
        self.page_image.load(path)


class PreviewLabel(QLabel):
    def __init__(self, text="页面预览", parent=None):
        super().__init__(text, parent)
        self._pixmap = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(220)
        self.setStyleSheet("background: #262b2e; border-radius: 7px; color: #aeb7bb;")

    def set_image(self, path):
        self._pixmap = QPixmap(str(path))
        self._rescale()

    def clear_image(self, text="页面预览"):
        self._pixmap = QPixmap()
        self.setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._pixmap.isNull():
            return
        self.setPixmap(self._pixmap.scaled(
            max(100, self.width() - 16), max(100, self.height() - 16),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


class DropZone(QFrame):
    dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("Card")
        self.setMinimumHeight(260)
        self.setStyleSheet("QFrame { border: 1px dashed #b7c2c6; border-radius: 12px; background: transparent; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("将扫描版 PDF 拖到这里")
        title.setStyleSheet("font-size: 18px; font-weight: 600; border: none;")
        detail = QLabel("支持中文书籍 · 本地识别 · 不联网上传文件")
        detail.setObjectName("Subtitle")
        detail.setStyleSheet("border: none;")
        self.hint = QLabel("选择 PDF 文件")
        self.hint.setStyleSheet("color: #2b7467; font-weight: 600; border: none;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(detail, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(18)
        layout.addWidget(self.hint, alignment=Qt.AlignmentFlag.AlignHCenter)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(
                url.toLocalFile().lower().endswith(".pdf") for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.dropped.emit(path)
                break

    def mousePressEvent(self, event):
        if callable(getattr(self, "on_click", None)):
            self.on_click()

