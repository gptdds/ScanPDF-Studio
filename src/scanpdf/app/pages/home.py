from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QPushButton, QVBoxLayout, QWidget)

from scanpdf.app.widgets import Card, DropZone


class HomePage(QWidget):
    choose_requested = Signal()
    file_dropped = Signal(str)
    project_requested = Signal(str)
    batch_requested = Signal()

    def __init__(self, history, queue, parent=None):
        super().__init__(parent)
        self.history = history
        self.queue = queue
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        top = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("扫描书，恢复成可读的书")
        title.setObjectName("PageTitle")
        subtitle = QLabel("本地 OCR、中文版面分析、章节识别与可重排 EPUB 3，一次完成。")
        subtitle.setObjectName("Subtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        top.addLayout(heading)
        top.addStretch()
        batch = QPushButton("批量转换")
        batch.clicked.connect(self.batch_requested)
        top.addWidget(batch, alignment=Qt.AlignmentFlag.AlignVCenter)
        choose = QPushButton("选择 PDF")
        choose.setObjectName("Primary")
        choose.clicked.connect(self.choose_requested)
        top.addWidget(choose, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(top)
        layout.addSpacing(18)
        self.drop = DropZone()
        self.drop.on_click = self.choose_requested.emit
        self.drop.dropped.connect(self.file_dropped)
        layout.addWidget(self.drop)
        layout.addSpacing(18)
        recent_head = QHBoxLayout()
        recent_title = QLabel("最近项目")
        recent_title.setObjectName("SectionTitle")
        recent_head.addWidget(recent_title)
        recent_head.addStretch()
        self.count_label = QLabel("")
        self.count_label.setObjectName("Meta")
        recent_head.addWidget(self.count_label)
        layout.addLayout(recent_head)
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        self.recent = QListWidget()
        self.recent.setMinimumHeight(150)
        self.recent.itemDoubleClicked.connect(self._open)
        card_layout.addWidget(self.recent)
        layout.addWidget(card, 1)
        queue_card = Card()
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(12, 10, 12, 10)
        queue_head = QHBoxLayout()
        queue_title = QLabel("批量队列 · 单任务顺序处理")
        queue_title.setObjectName("SectionTitle")
        queue_head.addWidget(queue_title)
        queue_head.addStretch()
        self.queue_count = QLabel("0 个任务")
        self.queue_count.setObjectName("Meta")
        queue_head.addWidget(self.queue_count)
        queue_layout.addLayout(queue_head)
        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(116)
        self.queue_list.itemDoubleClicked.connect(self._open_queue_item)
        queue_layout.addWidget(self.queue_list)
        queue_actions = QHBoxLayout()
        self.queue_start = QPushButton("开始队列")
        self.queue_start.setObjectName("Primary")
        self.queue_start.clicked.connect(self._start_queue)
        self.queue_pause = QPushButton("暂停队列")
        self.queue_pause.clicked.connect(self.queue.toggle_pause)
        self.queue_cancel = QPushButton("取消当前")
        self.queue_cancel.clicked.connect(self.queue.cancel_current)
        self.queue_stop = QPushButton("停止队列")
        self.queue_stop.setObjectName("Danger")
        self.queue_stop.clicked.connect(self.queue.stop)
        self.queue_clear = QPushButton("清除已完成")
        self.queue_clear.clicked.connect(self.queue.clear)
        for button in (self.queue_start, self.queue_pause, self.queue_cancel,
                       self.queue_stop, self.queue_clear):
            queue_actions.addWidget(button)
        queue_actions.addStretch()
        queue_layout.addLayout(queue_actions)
        layout.addWidget(queue_card)
        bottom = QHBoxLayout()
        note = QLabel("处理结果保存在本机项目目录；原始 OCR 结果不会被编辑覆盖。")
        note.setObjectName("Meta")
        bottom.addWidget(note)
        bottom.addStretch()
        open_folder = QPushButton("打开项目数据目录")
        open_folder.clicked.connect(self._open_data)
        bottom.addWidget(open_folder)
        layout.addLayout(bottom)
        self.queue.changed.connect(self.refresh_queue)
        self.refresh()
        self.refresh_queue()

    def refresh(self):
        self.recent.clear()
        records = self.history.records()
        for record in records:
            status = {"complete": "待校对", "exported": "已导出",
                      "processing": "处理中"}.get(record["status"], record["status"])
            confidence = f"{record['mean_confidence'] * 100:.0f}%"
            item = QListWidgetItem(
                f"{record['title']}    ·    {record['pages']} 页    ·    平均置信度 {confidence}"
                f"    ·    {status}\n{record['updated'].replace('T', ' ')}    "
                f"{Path(record['source']).name}")
            item.setData(Qt.ItemDataRole.UserRole, record["project"])
            item.setToolTip(record.get("output") or record["source"])
            self.recent.addItem(item)
        self.count_label.setText(f"{len(records)} 个本地项目" if records else "尚无转换记录")
        if not records:
            item = QListWidgetItem("完成第一本书后，项目会出现在这里。双击项目可继续校对。")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recent.addItem(item)

    def _open(self, item):
        project = item.data(Qt.ItemDataRole.UserRole)
        if project:
            self.project_requested.emit(project)

    def _open_data(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from scanpdf.services.paths import data_dir
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))

    def refresh_queue(self):
        jobs = self.queue.snapshot()
        self.queue_list.clear()
        active = [job for job in jobs if job["status"] in ("等待中", "处理中")]
        self.queue_count.setText(f"{len(active)} 个待处理" if active else f"{len(jobs)} 个任务")
        for job in jobs:
            suffix = f" · {job['progress']}%" if job["status"] == "处理中" else ""
            detail = job["message"] if job["status"] == "处理中" else (
                job["error"] or job["message"])
            item = QListWidgetItem(
                f"{job['title']}    ·    {job['status']}{suffix}"
                + (f"    ·    {detail}" if detail else ""))
            item.setData(Qt.ItemDataRole.UserRole, job)
            if job["status"] == "失败":
                item.setForeground(Qt.GlobalColor.darkRed)
            elif job["status"] == "已导出":
                item.setForeground(Qt.GlobalColor.darkGreen)
            self.queue_list.addItem(item)
        running = self.queue.running
        has_waiting = any(job["status"] == "等待中" for job in jobs)
        self.queue_start.setEnabled(has_waiting and not running)
        self.queue_pause.setEnabled(running)
        self.queue_pause.setText("继续队列" if self.queue.paused else "暂停队列")
        self.queue_cancel.setEnabled(running)
        self.queue_stop.setEnabled(any(job["status"] in ("等待中", "处理中") for job in jobs))
        self.queue_clear.setEnabled(any(job["status"] not in ("等待中", "处理中") for job in jobs))

    def _start_queue(self):
        if not self.queue.start():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "队列未启动",
                                    "当前工作台仍有任务，或队列中没有等待任务。")
        self.refresh_queue()

    def _open_queue_item(self, item):
        job = item.data(Qt.ItemDataRole.UserRole)
        if job and job.get("project"):
            self.project_requested.emit(job["project"])

