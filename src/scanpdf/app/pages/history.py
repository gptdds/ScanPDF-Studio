from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from scanpdf.services.checkpoint_manager import ProjectStore


class HistoryPage(QWidget):
    project_requested = Signal(str)
    changed = Signal()

    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.history = history
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        title = QLabel("转换历史")
        title.setObjectName("PageTitle")
        subtitle = QLabel("本地项目记录。双击一行可重新打开校对，项目文件不会因历史记录删除而丢失。")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(16)
        toolbar = QHBoxLayout()
        self.summary = QLabel("")
        self.summary.setObjectName("Meta")
        toolbar.addWidget(self.summary)
        toolbar.addStretch()
        refresh = QPushButton("刷新")
        refresh.clicked.connect(self.refresh)
        toolbar.addWidget(refresh)
        self.open_button = QPushButton("重新打开项目")
        self.open_button.setObjectName("Primary")
        self.open_button.clicked.connect(self.open_selected)
        toolbar.addWidget(self.open_button)
        layout.addLayout(toolbar)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["书名", "转换时间", "页数", "平均置信度", "输出路径", "状态"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 145)
        self.table.setColumnWidth(2, 65)
        self.table.setColumnWidth(3, 105)
        self.table.setColumnWidth(4, 300)
        self.table.itemDoubleClicked.connect(lambda _: self.open_selected())
        self.table.itemSelectionChanged.connect(self._update_actions)
        layout.addWidget(self.table, 1)
        footer = QHBoxLayout()
        open_output = QPushButton("打开输出文件夹")
        open_output.clicked.connect(self.open_output)
        open_source = QPushButton("打开源 PDF")
        open_source.clicked.connect(self.open_source)
        forget = QPushButton("从历史中移除")
        forget.setObjectName("Danger")
        forget.clicked.connect(self.forget_selected)
        footer.addWidget(open_output)
        footer.addWidget(open_source)
        footer.addStretch()
        footer.addWidget(forget)
        layout.addLayout(footer)
        self.refresh()

    def refresh(self):
        records = self.history.records(500)
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = [record["title"], record["updated"].replace("T", " "),
                      str(record["pages"]),
                      f"{record['mean_confidence'] * 100:.1f}%" if record["mean_confidence"] else "–",
                      record.get("output") or record["source"],
                      {"complete": "待校对", "exported": "已导出",
                       "processing": "未完成"}.get(record["status"], record["status"])]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record)
                if column == 5 and record["status"] == "processing":
                    item.setForeground(Qt.GlobalColor.darkYellow)
                if column in (2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
        self.summary.setText(f"{len(records)} 个项目")
        self._update_actions()

    def _record(self):
        row = self.table.currentRow()
        if row < 0 or not self.table.item(row, 0):
            return None
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _update_actions(self):
        self.open_button.setEnabled(self._record() is not None)

    def open_selected(self):
        record = self._record()
        if not record:
            return
        if not Path(record["project"]).exists():
            QMessageBox.warning(self, "项目不可用", "项目目录已被删除或移动，无法重新打开。")
            return
        self.project_requested.emit(record["project"])

    def open_output(self):
        record = self._record()
        if not record:
            return
        output = Path(record.get("output") or "")
        target = output.parent if output.name else Path(record["project"])
        if target.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        else:
            QMessageBox.information(self, "目录不存在", "输出目录尚未创建。")

    def open_source(self):
        record = self._record()
        if record and Path(record["source"]).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(record["source"]))

    def forget_selected(self):
        record = self._record()
        if not record:
            return
        if QMessageBox.question(self, "移除历史记录",
                                "只移除历史记录，不会删除项目文件或导出的 EPUB。") != QMessageBox.StandardButton.Yes:
            return
        self.history.delete(record["project"])
        self.refresh()
        self.changed.emit()

