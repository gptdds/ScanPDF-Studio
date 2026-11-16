import threading
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                               QSplitter, QTextEdit, QVBoxLayout, QWidget)

from scanpdf.app.widgets import Card, PreviewLabel
from scanpdf.core.epub_builder import epubcheck, validate_epub
from scanpdf.core.pdf_loader import PDFDocument
from scanpdf.models import Settings
from scanpdf.pipeline import Cancelled, Pipeline, export_project
from scanpdf.services.checkpoint_manager import ProjectStore
from scanpdf.services.paths import data_dir


class PipelineThread(QThread):
    progress = Signal(int, str)
    page_ready = Signal(int)
    succeeded = Signal()
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, project_directory, cancel_event, pause_event, parent=None):
        super().__init__(parent)
        self.project_directory = project_directory
        self.cancel_event = cancel_event
        self.pause_event = pause_event

    def run(self):
        try:
            pipeline = Pipeline(self.project_directory,
                                lambda value, message: self.progress.emit(value, message),
                                self.cancel_event.is_set, self.pause_event.is_set,
                                lambda number: self.page_ready.emit(number))
            pipeline.run()
            self.succeeded.emit()
        except Cancelled:
            self.stopped.emit()
        except Exception:
            self.failed.emit(traceback.format_exc())


class WorkspacePage(QWidget):
    review_requested = Signal(str)
    completed = Signal()
    status_changed = Signal(str)

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.pdf_path = None
        self.store = None
        self.project = None
        self.pages = {}
        self.thread = None
        self.cancel_event = threading.Event()
        self.pause_event = threading.Event()
        self.draft = True
        self.start_guard = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        self.title = QLabel("转换工作台")
        self.title.setObjectName("PageTitle")
        self.subtitle = QLabel("选择 PDF 后开始")
        self.subtitle.setObjectName("Subtitle")
        heading.addWidget(self.title)
        heading.addWidget(self.subtitle)
        header.addLayout(heading)
        header.addStretch()
        self.status_pill = QLabel("准备就绪")
        self.status_pill.setObjectName("Pill")
        header.addWidget(self.status_pill, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = Card()
        left.setMinimumWidth(320)
        left.setMaximumWidth(410)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(20, 18, 20, 18)
        left_layout.setSpacing(10)
        file_title = QLabel("文件与输出")
        file_title.setObjectName("SectionTitle")
        left_layout.addWidget(file_title)
        self.file_name = QLabel("未选择文件")
        self.file_name.setWordWrap(True)
        self.file_name.setStyleSheet("font-weight: 600;")
        left_layout.addWidget(self.file_name)
        self.file_meta = QLabel("")
        self.file_meta.setObjectName("Meta")
        self.file_meta.setWordWrap(True)
        left_layout.addWidget(self.file_meta)
        left_layout.addSpacing(4)
        left_layout.addWidget(QLabel("书名"))
        self.book_title = QLineEdit()
        self.book_title.setPlaceholderText("EPUB 书名")
        left_layout.addWidget(self.book_title)
        left_layout.addWidget(QLabel("作者"))
        self.author = QLineEdit()
        self.author.setPlaceholderText("未知")
        left_layout.addWidget(self.author)
        left_layout.addWidget(QLabel("输出文件"))
        output_row = QHBoxLayout()
        self.output = QLineEdit()
        browse = QPushButton("…")
        browse.setFixedWidth(38)
        browse.setToolTip("选择 EPUB 输出位置")
        browse.clicked.connect(self.choose_output)
        output_row.addWidget(self.output, 1)
        output_row.addWidget(browse)
        left_layout.addLayout(output_row)
        left_layout.addSpacing(8)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        left_layout.addWidget(self.progress)
        self.progress_text = QLabel("等待开始")
        self.progress_text.setObjectName("Meta")
        self.progress_text.setWordWrap(True)
        left_layout.addWidget(self.progress_text)
        metrics = QHBoxLayout()
        self.page_metric = QLabel("0")
        self.page_metric.setObjectName("Metric")
        self.confidence_metric = QLabel("–")
        self.confidence_metric.setObjectName("Metric")
        metric_left = QVBoxLayout()
        metric_left.addWidget(self.page_metric)
        metric_left.addWidget(QLabel("已识别页"))
        metric_right = QVBoxLayout()
        metric_right.addWidget(self.confidence_metric)
        metric_right.addWidget(QLabel("平均置信度"))
        metrics.addLayout(metric_left)
        metrics.addSpacing(30)
        metrics.addLayout(metric_right)
        metrics.addStretch()
        left_layout.addLayout(metrics)
        buttons = QHBoxLayout()
        self.start_button = QPushButton("开始识别")
        self.start_button.setObjectName("Primary")
        self.start_button.clicked.connect(self.start)
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setObjectName("Danger")
        self.cancel_button.clicked.connect(self.cancel)
        self.cancel_button.setEnabled(False)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.cancel_button)
        left_layout.addLayout(buttons)
        self.review_button = QPushButton("进入 OCR 校对")
        self.review_button.clicked.connect(self.open_review)
        left_layout.addWidget(self.review_button)
        self.export_button = QPushButton("导出 EPUB 3")
        self.export_button.clicked.connect(self.export)
        left_layout.addWidget(self.export_button)
        left_layout.addStretch()
        log_label = QLabel("处理日志")
        log_label.setObjectName("SectionTitle")
        left_layout.addWidget(log_label)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(140)
        self.log.setPlaceholderText("识别进度、警告与重试会记录在这里。")
        left_layout.addWidget(self.log)
        splitter.addWidget(left)
        right = QSplitter(Qt.Orientation.Vertical)
        image_card = Card()
        image_layout = QVBoxLayout(image_card)
        image_layout.setContentsMargins(14, 12, 14, 14)
        image_head = QHBoxLayout()
        image_head.addWidget(QLabel("扫描页面"))
        image_head.addStretch()
        self.image_page = QLabel("第 – 页")
        self.image_page.setObjectName("Meta")
        image_head.addWidget(self.image_page)
        image_layout.addLayout(image_head)
        self.preview = PreviewLabel()
        image_layout.addWidget(self.preview, 1)
        right.addWidget(image_card)
        text_card = Card()
        text_layout = QVBoxLayout(text_card)
        text_layout.setContentsMargins(14, 12, 14, 14)
        text_head = QHBoxLayout()
        text_head.addWidget(QLabel("OCR 文字预览"))
        text_head.addStretch()
        self.warning_label = QLabel("")
        self.warning_label.setObjectName("WarningPill")
        self.warning_label.hide()
        text_head.addWidget(self.warning_label)
        text_layout.addLayout(text_head)
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setPlaceholderText("完成页面识别后，这里显示结构化文字。")
        text_layout.addWidget(self.text_preview, 1)
        right.addWidget(text_card)
        right.setSizes([520, 280])
        splitter.addWidget(right)
        splitter.setSizes([360, 880])
        layout.addWidget(splitter, 1)
        self._set_actions(False, False, False)

    def _set_actions(self, running, paused=False, can_export=False):
        self.start_button.setEnabled(not running)
        self.pause_button.setEnabled(running)
        self.cancel_button.setEnabled(running)
        self.review_button.setEnabled(can_export and not running)
        self.export_button.setEnabled(can_export and not running)
        if running:
            self.pause_button.setText("继续" if paused else "暂停")
        else:
            self.pause_button.setText("暂停")

    def set_file(self, path):
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "任务正在进行", "请先等待当前任务完成或取消。")
            return False
        try:
            with PDFDocument(path) as pdf:
                count = pdf.page_count
                first = pdf.render(1, 150)
        except Exception as exc:
            QMessageBox.critical(self, "无法打开 PDF", str(exc))
            return False
        self.pdf_path = str(Path(path).resolve())
        self.store = None
        self.project = None
        self.pages = {}
        self.draft = True
        self.title.setText(Path(path).stem)
        self.subtitle.setText("扫描版 PDF · 本地 OCR 转换")
        self.file_name.setText(Path(path).name)
        self.file_meta.setText(f"{count} 页 · {Path(path).parent}")
        self.book_title.setText(Path(path).stem)
        self.author.setText("未知")
        default_output = Path.home() / "Desktop" / f"{Path(path).stem}.epub"
        self.output.setText(str(default_output))
        self.progress.setValue(0)
        self.progress_text.setText("等待开始 · 模型在首次使用时下载")
        self.page_metric.setText("0")
        self.confidence_metric.setText("–")
        self.status_pill.setText("准备就绪")
        self.log.clear()
        self.text_preview.clear()
        self.warning_label.hide()
        self.preview.clear_image(f"{count} 页 · 点击开始识别")
        self.image_page.setText("第 1 页")
        self.start_button.setText("开始识别")
        self._set_actions(False, False, False)
        return True

    def load_project(self, directory):
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "任务正在进行", "请先等待当前任务完成或取消。")
            return False
        try:
            store = ProjectStore.open(directory)
            project = store.load()
        except Exception as exc:
            QMessageBox.critical(self, "无法打开项目", str(exc))
            return False
        self.store = store
        self.project = project
        self.pdf_path = project["pdf"]
        self.draft = False
        self.title.setText(project["title"])
        self.subtitle.setText("本地项目 · 可继续校对与导出")
        self.file_name.setText(Path(project["pdf"]).name)
        self.file_meta.setText(f"{project.get('total_pages', 0)} 页 · {project['created']}")
        self.book_title.setText(project["title"])
        self.author.setText(project.get("author", "未知"))
        self.output.setText(project.get("output") or
                            str(Path.home() / "Desktop" / f"{project['title']}.epub"))
        self.pages = {page.number: page for page in store.load_pages()}
        completed = len([page for page in self.pages.values() if page.width])
        total = max(project.get("total_pages", 0), completed)
        self.progress.setValue(int(100 * completed / total) if total else 0)
        self.progress_text.setText(f"已保存 {completed} / {total} 页")
        self.page_metric.setText(str(completed))
        self._refresh_confidence()
        self.status_pill.setText({"complete": "待校对", "exported": "已导出",
                                  "processing": "未完成"}.get(project.get("status"), "未完成"))
        self.log.clear()
        self.log.appendPlainText(f"项目已恢复：{directory}")
        if completed:
            self._show_page(max(self.pages))
            self._set_actions(False, False, True)
            self.start_button.setText("续跑未完成页" if project.get("status") != "complete" else "重新检查")
        else:
            self._set_actions(False, False, False)
        return True

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "选择 EPUB 输出路径",
                                              self.output.text(), "EPUB 电子书 (*.epub)")
        if path:
            if not path.lower().endswith(".epub"):
                path += ".epub"
            self.output.setText(path)

    def _create_project(self):
        settings = self.settings_manager.settings()
        root = data_dir() / "projects"
        root.mkdir(parents=True, exist_ok=True)
        from uuid import uuid4
        store = ProjectStore(root / uuid4().hex)
        project = store.initialize(self.pdf_path, settings, self.output.text())
        project["title"] = self.book_title.text().strip() or Path(self.pdf_path).stem
        project["author"] = self.author.text().strip() or "未知"
        store.save(project)
        self.store, self.project = store, project
        self.draft = False

    def start(self):
        if not self.pdf_path:
            return
        if self.start_guard and not self.start_guard():
            QMessageBox.information(self, "批量队列正在运行",
                                    "为避免内存争用，请等待批量队列暂停或完成后再开始。")
            return
        if not self.draft and self.store:
            self.project["title"] = self.book_title.text().strip() or self.project["title"]
            self.project["author"] = self.author.text().strip() or "未知"
            self.project["output"] = self.output.text()
            self.store.save(self.project)
        else:
            self._create_project()
        self.cancel_event.clear()
        self.pause_event.clear()
        self.thread = PipelineThread(str(self.store.directory), self.cancel_event, self.pause_event, self)
        self.thread.progress.connect(self._on_progress)
        self.thread.page_ready.connect(self._on_page_ready)
        self.thread.succeeded.connect(self._on_success)
        self.thread.failed.connect(self._on_failure)
        self.thread.stopped.connect(self._on_stopped)
        self.thread.finished.connect(self._thread_finished)
        self.log.appendPlainText("开始处理；每页完成后自动保存检查点。")
        self.status_pill.setText("正在识别")
        self.status_changed.emit("正在识别")
        self._set_actions(True, False, False)
        self.start_button.setText("处理中…")
        self.thread.start()

    def toggle_pause(self):
        if not self.thread or not self.thread.isRunning():
            return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.status_pill.setText("正在识别")
            self._set_actions(True, False, False)
            self.progress_text.setText("继续处理")
        else:
            self.pause_event.set()
            self.status_pill.setText("已暂停")
            self._set_actions(True, True, False)
            self.progress_text.setText("将在当前页完成后暂停")

    def cancel(self):
        if not self.thread or not self.thread.isRunning():
            return
        if QMessageBox.question(self, "取消任务",
                                "将在当前页完成后停止。已完成的页面会保留，可稍后续跑。") != QMessageBox.StandardButton.Yes:
            return
        self.cancel_event.set()
        self.status_pill.setText("正在取消")
        self.cancel_button.setEnabled(False)

    def _on_progress(self, value, message):
        self.progress.setValue(value)
        self.progress_text.setText(message)
        if message and (not self.log.toPlainText().endswith(message)):
            self.log.appendPlainText(message)
            if "失败" in message or "警告" in message or "降级" in message:
                self.status_pill.setObjectName("WarningPill")
                self.status_pill.style().unpolish(self.status_pill)
                self.status_pill.style().polish(self.status_pill)

    def _on_page_ready(self, number):
        if self.store:
            page = self.store.load_page(number)
            if page:
                self.pages[number] = page
            self.page_metric.setText(str(len([page for page in self.pages.values() if page.width])))
            self._refresh_confidence()
            if self.pages:
                self._show_page(max(self.pages))

    def _refresh_confidence(self):
        scores = [block.confidence for page in self.pages.values()
                  for block in page.blocks if block.text.strip()]
        self.confidence_metric.setText(f"{sum(scores) / len(scores) * 100:.0f}%" if scores else "–")

    def _show_page(self, number):
        page = self.pages.get(number)
        if not page:
            return
        self.image_page.setText(f"第 {number} 页")
        image = self.store.directory / page.image if page.image and self.store else None
        if image and image.exists():
            self.preview.set_image(image)
        else:
            self.preview.clear_image("页面处理失败或不可用")
        chunks = []
        threshold = self.settings_manager.settings().low_confidence
        for block in sorted(page.blocks, key=lambda item: item.reading_order):
            if block.excluded:
                continue
            if block.block_type in ("image", "table", "formula"):
                chunks.append(f"<p style='color:#7c898f'>[{block.block_type}] {block.text}</p>")
            else:
                color = "#b44a3a" if block.confidence < threshold else "#283137"
                underline = " text-decoration: underline;" if block.confidence < threshold else ""
                chunks.append(f"<p style='color:{color};{underline} margin:0 0 7px 0'>"
                              f"{self._escape(block.text)}</p>")
        self.text_preview.setHtml("".join(chunks) or "<p style='color:#7c898f'>本页无文字。</p>")
        warnings = page.warnings
        if warnings:
            self.warning_label.setText(f"{len(warnings)} 条提示")
            self.warning_label.setToolTip("\n".join(warnings))
            self.warning_label.show()
        else:
            self.warning_label.hide()

    @staticmethod
    def _escape(text):
        import html
        return html.escape(text)

    def _on_success(self):
        self.project = self.store.load()
        self.pages = {page.number: page for page in self.store.load_pages()}
        self.progress.setValue(100)
        self.progress_text.setText(f"完成 · 共 {len(self.pages)} 页，可校对或导出")
        self.status_pill.setText("待校对")
        self.status_pill.setObjectName("Pill")
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)
        self.log.appendPlainText("全部页面处理结束。未识别文字或警告页面保留在项目中，请进入校对台检查。")
        self._refresh_confidence()
        if self.pages:
            self._show_page(max(self.pages))
        self.completed.emit()
        self.status_changed.emit("待校对")

    def _on_failure(self, message):
        self.log.appendPlainText(message[-3000:])
        self.status_pill.setText("处理错误")
        QMessageBox.critical(self, "任务未完成",
                             "处理过程发生错误。已完成的页面检查点仍然保留。\n\n"
                             + message.strip().splitlines()[-1])

    def _on_stopped(self):
        self.log.appendPlainText("任务已取消；已完成页面已保存。")
        self.status_pill.setText("已取消")
        self.progress_text.setText("可重新打开项目续跑未完成页")
        self.status_changed.emit("已取消")

    def _thread_finished(self):
        self.thread = None
        can_export = bool(self.pages)
        self._set_actions(False, False, can_export)
        self.start_button.setText("续跑未完成页" if self.project and
                                  self.project.get("status") != "complete" else "重新检查")
        if self.project:
            self.project = self.store.load()
            self.pages = {page.number: page for page in self.store.load_pages()}

    def open_review(self):
        if not self.store:
            return
        if self.thread and self.thread.isRunning():
            return
        self.project["title"] = self.book_title.text().strip() or self.project["title"]
        self.project["author"] = self.author.text().strip() or "未知"
        self.project["output"] = self.output.text()
        self.store.save(self.project)
        self.review_requested.emit(str(self.store.directory))

    def export(self):
        if not self.store:
            return
        self.project["title"] = self.book_title.text().strip() or self.project["title"]
        self.project["author"] = self.author.text().strip() or "未知"
        self.project["output"] = self.output.text()
        self.store.save(self.project)
        try:
            path = export_project(str(self.store.directory), self.output.text())
            validation = validate_epub(path)
            external = epubcheck(path) if validation["ok"] else {"ok": None, "message": ""}
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        message = f"已生成 {path}\n\n内置结构验证：" + ("通过" if validation["ok"] else "未通过")
        if external["ok"] is not None:
            message += "\nEPUBCheck：" + ("通过" if external["ok"] else "未通过")
            if not external["ok"] and external.get("message"):
                message += "\n" + external["message"][-1200:]
        elif external["message"]:
            message += "\n" + external["message"]
        if validation["errors"]:
            message += "\n" + "\n".join(validation["errors"])
        if validation["warnings"]:
            message += "\n提示：" + "\n".join(validation["warnings"])
        box = QMessageBox(self)
        box.setWindowTitle("EPUB 3 导出完成")
        box.setText(message)
        box.setIcon(QMessageBox.Icon.Information if validation["ok"] else QMessageBox.Icon.Warning)
        open_button = box.addButton("打开所在文件夹", QMessageBox.ButtonRole.ActionRole)
        box.addButton("关闭", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() == open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
        self.status_pill.setText("已导出")
        self.completed.emit()

    def busy(self):
        return bool(self.thread and self.thread.isRunning())

