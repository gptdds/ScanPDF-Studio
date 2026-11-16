from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QFrame,
                               QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from scanpdf.app.pages.history import HistoryPage
from scanpdf.app.pages.home import HomePage
from scanpdf.app.pages.preferences import PreferencesPage
from scanpdf.app.pages.review import ReviewPage
from scanpdf.app.pages.workspace import WorkspacePage
from scanpdf.app.theme import DARK, LIGHT
from scanpdf.services.history_manager import HistoryManager
from scanpdf.services.settings_manager import SettingsManager
from scanpdf.services.task_queue import BatchQueue


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScanPDF Studio")
        self.resize(1360, 860)
        self.setMinimumSize(1120, 720)
        self.settings_manager = SettingsManager()
        self.history = HistoryManager()
        self.queue = BatchQueue(guard=lambda: not self.workspace.busy() if hasattr(self, "workspace") else True, parent=self)
        self.setAcceptDrops(True)
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(214)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 20, 16, 16)
        side_layout.setSpacing(6)
        brand = QHBoxLayout()
        mark = QLabel("SP")
        mark.setObjectName("BrandMark")
        mark.setFixedSize(34, 34)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.addWidget(mark)
        brand_text = QVBoxLayout()
        name = QLabel("ScanPDF Studio")
        name.setObjectName("Brand")
        edition = QLabel("扫描书 · EPUB 3")
        edition.setObjectName("Meta")
        brand_text.addWidget(name)
        brand_text.addWidget(edition)
        brand.addLayout(brand_text)
        side_layout.addLayout(brand)
        side_layout.addSpacing(22)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = {}
        for key, label in (("home", "首页"), ("workspace", "转换工作台"),
                           ("review", "OCR 校对"), ("history", "转换历史"),
                           ("settings", "处理设置")):
            button = QPushButton(label)
            button.setObjectName("Nav")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, target=key: self.navigate(target))
            self.nav_group.addButton(button)
            self.nav_buttons[key] = button
            side_layout.addWidget(button)
            if key == "workspace":
                side_layout.addSpacing(12)
        side_layout.addStretch()
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #d9dfe1;")
        side_layout.addWidget(divider)
        self.task_status = QLabel("空闲")
        self.task_status.setObjectName("Meta")
        self.task_status.setWordWrap(True)
        side_layout.addWidget(self.task_status)
        theme_button = QPushButton("切换深色主题")
        theme_button.setObjectName("Link")
        theme_button.clicked.connect(self.toggle_theme)
        self.theme_button = theme_button
        side_layout.addWidget(theme_button)
        version = QLabel("0.1.1 · 本地处理")
        version.setObjectName("Meta")
        side_layout.addWidget(version)
        shell.addWidget(sidebar)
        self.stack = QStackedWidget()
        shell.addWidget(self.stack, 1)
        self.home = HomePage(self.history, self.queue)
        self.workspace = WorkspacePage(self.settings_manager)
        self.workspace.start_guard = lambda: not self.queue.running
        self.review = ReviewPage(self.settings_manager)
        self.history_page = HistoryPage(self.history)
        self.preferences = PreferencesPage(self.settings_manager)
        self.pages = {"home": self.home, "workspace": self.workspace,
                      "review": self.review, "history": self.history_page,
                      "settings": self.preferences}
        for page in self.pages.values():
            self.stack.addWidget(page)
        self.home.choose_requested.connect(self.choose_pdf)
        self.home.file_dropped.connect(self.open_pdf)
        self.home.project_requested.connect(self.open_project)
        self.home.batch_requested.connect(self.choose_batch)
        self.workspace.review_requested.connect(self.open_review)
        self.workspace.completed.connect(self._refresh_history)
        self.workspace.status_changed.connect(self.task_status.setText)
        self.queue.changed.connect(self._queue_status)
        self.queue.message.connect(self.statusBar().showMessage)
        self.review.back_requested.connect(lambda: self.navigate("workspace"))
        self.review.completed.connect(self._refresh_history)
        self.history_page.project_requested.connect(self.open_project)
        self.history_page.changed.connect(self._refresh_history)
        self.preferences.saved.connect(self.apply_theme)
        self.navigate("home")
        self.apply_theme()
        self.statusBar().showMessage("就绪 · 所有 OCR 均在本机完成")
        self._install_shortcuts()

    def _install_shortcuts(self):
        open_action = QAction(self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.choose_pdf)
        self.addAction(open_action)
        home_action = QAction(self)
        home_action.setShortcut(QKeySequence("Ctrl+1"))
        home_action.triggered.connect(lambda: self.navigate("home"))
        self.addAction(home_action)

    def navigate(self, key):
        if key == "review" and not self.review.store:
            if self.workspace.store:
                self.review.open_project(str(self.workspace.store.directory))
            else:
                QMessageBox.information(self, "尚无项目", "请先导入 PDF 并完成识别。")
                return
        self.stack.setCurrentWidget(self.pages[key])
        self.nav_buttons[key].setChecked(True)
        if key == "home":
            self.home.refresh()
        elif key == "history":
            self.history_page.refresh()
        elif key == "review" and self.workspace.store:
            self.review.open_project(str(self.workspace.store.directory))

    def choose_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择扫描版 PDF", "",
                                              "PDF 文件 (*.pdf)")
        if path:
            self.open_pdf(path)

    def choose_batch(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "批量选择扫描版 PDF", "",
                                                "PDF 文件 (*.pdf)")
        if not paths:
            return
        self.queue.set_settings(self.settings_manager.settings())
        self.queue.add(paths, self.settings_manager.settings())
        self.home.refresh_queue()
        self.statusBar().showMessage(f"已加入 {len(paths)} 本书，点击“开始队列”顺序处理")

    def open_pdf(self, path):
        if self.queue.running:
            QMessageBox.information(self, "批量队列运行中",
                                    "可先暂停或停止队列，再打开工作台处理另一本书。")
            return
        if self.workspace.busy():
            QMessageBox.warning(self, "任务进行中", "请先等待当前任务完成或取消。")
            return
        if self.workspace.set_file(path):
            self.stack.setCurrentWidget(self.workspace)
            self.nav_buttons["workspace"].setChecked(True)
            self.statusBar().showMessage(f"已载入 {Path(path).name}")

    def open_project(self, directory):
        if self.workspace.busy():
            QMessageBox.warning(self, "任务进行中", "请先等待当前任务完成或取消。")
            return
        if self.workspace.load_project(directory):
            self.stack.setCurrentWidget(self.workspace)
            self.nav_buttons["workspace"].setChecked(True)
            self.statusBar().showMessage(f"已恢复项目 {Path(directory).name}")

    def open_review(self, directory):
        if self.review.open_project(directory):
            self.stack.setCurrentWidget(self.review)
            self.nav_buttons["review"].setChecked(True)

    def _refresh_history(self):
        self.home.refresh()
        self.history_page.refresh()

    def _queue_status(self):
        jobs = self.queue.snapshot()
        active = [job for job in jobs if job["status"] == "处理中"]
        if active:
            job = active[0]
            self.task_status.setText(f"队列 · {job['title']} · {job['progress']}%")
        elif self.queue.running:
            self.task_status.setText("批量队列运行中")
        elif any(job["status"] == "已导出" for job in jobs):
            self.task_status.setText("批量队列完成")
            self._refresh_history()

    def apply_theme(self):
        theme = self.settings_manager.data.get("theme", "light")
        QApplication.instance().setStyleSheet(DARK if theme == "dark" else LIGHT)
        self.theme_button.setText("切换浅色主题" if theme == "dark" else "切换深色主题")

    def toggle_theme(self):
        new_theme = "light" if self.settings_manager.data.get("theme") == "dark" else "dark"
        self.settings_manager.save(self.settings_manager.settings(), theme=new_theme)
        self.preferences.load()
        self.apply_theme()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(
                url.toLocalFile().lower().endswith(".pdf") for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.toLocalFile().lower().endswith(".pdf"):
                self.open_pdf(url.toLocalFile())
                return

    def closeEvent(self, event):
        if self.workspace.busy():
            answer = QMessageBox.question(
                self, "任务仍在进行",
                "关闭程序将取消当前识别。已完成页面会保留，可稍后续跑。确定退出？")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.workspace.cancel_event.set()
            self.workspace.pause_event.clear()
            self.workspace.thread.wait(8000)
        if self.queue.running:
            self.queue.stop()
            self.queue.wait(8000)
        event.accept()

