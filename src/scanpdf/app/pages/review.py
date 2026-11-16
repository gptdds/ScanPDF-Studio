import copy
import html
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton,
                               QSplitter, QTextEdit, QVBoxLayout, QWidget)
from PySide6.QtGui import QUndoCommand, QUndoStack

from scanpdf.app.widgets import Card, ImageViewer
from scanpdf.core.epub_builder import epubcheck, validate_epub
from scanpdf.models import Block
from scanpdf.pipeline import export_project
from scanpdf.services.checkpoint_manager import ProjectStore


LABELS = {"body": "正文", "heading": "标题", "caption": "图注", "table": "表格",
          "image": "图片", "formula": "公式", "footnote": "脚注", "note": "注释",
          "header": "页眉", "footer": "页脚", "page_number": "页码"}


def inverse_display_blocks(page):
    if not page.transform:
        return page.blocks
    try:
        matrix = np.linalg.inv(np.asarray(page.transform, dtype=float))
    except (ValueError, np.linalg.LinAlgError):
        return page.blocks
    result = []
    for block in page.blocks:
        clone = copy.copy(block)
        points = np.column_stack([np.asarray(block.bounding_box, dtype=float),
                                  np.ones(len(block.bounding_box))])
        mapped = (matrix @ points.T).T
        mapped = mapped[:, :2] / mapped[:, 2:3]
        clone.bounding_box = mapped.tolist()
        result.append(clone)
    return result


class BlocksCommand(QUndoCommand):
    def __init__(self, page, before, after, callback, text):
        super().__init__(text)
        self.page = page
        self.before = before
        self.after = after
        self.callback = callback

    def redo(self):
        self.page.blocks = copy.deepcopy(self.after)
        self.callback()

    def undo(self):
        self.page.blocks = copy.deepcopy(self.before)
        self.callback()


class ReviewPage(QWidget):
    completed = Signal()
    back_requested = Signal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.store = None
        self.project = None
        self.pages = []
        self.index = 0
        self.current_block_id = None
        self.undo_stack = QUndoStack(self)
        self.undo_stack.indexChanged.connect(lambda _: self._refresh_history_buttons())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(10)
        header = QHBoxLayout()
        back = QPushButton("返回工作台")
        back.setObjectName("Link")
        back.clicked.connect(self.back_requested)
        header.addWidget(back)
        heading = QVBoxLayout()
        self.title = QLabel("OCR 校对")
        self.title.setObjectName("PageTitle")
        self.subtitle = QLabel("选择文字框定位原图；修改会自动保存为检查点。")
        self.subtitle.setObjectName("Subtitle")
        heading.addWidget(self.title)
        heading.addWidget(self.subtitle)
        header.addSpacing(10)
        header.addLayout(heading)
        header.addStretch()
        self.save_state = QLabel("未打开项目")
        self.save_state.setObjectName("Pill")
        header.addWidget(self.save_state)
        self.export_button = QPushButton("导出校对后 EPUB")
        self.export_button.setObjectName("Primary")
        self.export_button.clicked.connect(self.export)
        header.addWidget(self.export_button)
        layout.addLayout(header)
        nav = QHBoxLayout()
        self.previous_button = QPushButton("上一页")
        self.previous_button.clicked.connect(lambda: self.change_page(-1))
        self.next_button = QPushButton("下一页")
        self.next_button.clicked.connect(lambda: self.change_page(1))
        self.page_label = QLabel("第 – 页")
        self.undo_button = QPushButton("撤销")
        self.undo_button.clicked.connect(self.undo_stack.undo)
        self.redo_button = QPushButton("重做")
        self.redo_button.clicked.connect(self.undo_stack.redo)
        nav.addWidget(self.previous_button)
        nav.addWidget(self.next_button)
        nav.addSpacing(12)
        nav.addWidget(self.page_label)
        nav.addStretch()
        nav.addWidget(self.undo_button)
        nav.addWidget(self.redo_button)
        layout.addLayout(nav)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        image_card = Card()
        image_layout = QVBoxLayout(image_card)
        image_layout.setContentsMargins(8, 8, 8, 8)
        legend = QHBoxLayout()
        legend.addWidget(QLabel("原始扫描页"))
        legend.addStretch()
        low = QLabel("低置信度")
        low.setStyleSheet("color: #c07b21;")
        legend.addWidget(low)
        selected = QLabel("当前")
        selected.setStyleSheet("color: #c34d3b;")
        legend.addWidget(selected)
        image_layout.addLayout(legend)
        self.viewer = ImageViewer()
        self.viewer.page_image.clicked.connect(self._clicked_image)
        image_layout.addWidget(self.viewer, 1)
        splitter.addWidget(image_card)
        text_area = QWidget()
        text_layout = QVBoxLayout(text_area)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(8)
        list_card = Card()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_head = QHBoxLayout()
        list_head.addWidget(QLabel("结构化文字框"))
        list_head.addStretch()
        self.low_count = QLabel("")
        self.low_count.setObjectName("WarningPill")
        list_head.addWidget(self.low_count)
        list_layout.addLayout(list_head)
        self.blocks = QListWidget()
        self.blocks.currentItemChanged.connect(self._selected)
        list_layout.addWidget(self.blocks, 1)
        text_layout.addWidget(list_card, 4)
        editor_card = Card()
        editor_layout = QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(12, 10, 12, 12)
        editor_head = QHBoxLayout()
        self.editor_type = QLabel("选择文字框以编辑")
        self.editor_type.setObjectName("SectionTitle")
        editor_head.addWidget(self.editor_type)
        editor_head.addStretch()
        self.confidence = QLabel("")
        self.confidence.setObjectName("Meta")
        editor_head.addWidget(self.confidence)
        editor_layout.addLayout(editor_head)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("点击上方文字框或左侧图像区域。")
        self.editor.setEnabled(False)
        self.editor.setMaximumHeight(125)
        editor_layout.addWidget(self.editor)
        structure = QHBoxLayout()
        structure.addWidget(QLabel("结构"))
        self.type_combo = QComboBox()
        for key, label in LABELS.items():
            self.type_combo.addItem(label, key)
        structure.addWidget(self.type_combo)
        structure.addWidget(QLabel("标题层级"))
        self.level_combo = QComboBox()
        for level in (1, 2, 3):
            self.level_combo.addItem(f"{level} 级", level)
        structure.addWidget(self.level_combo)
        self.structure_button = QPushButton("应用结构")
        self.structure_button.clicked.connect(self.apply_structure)
        structure.addWidget(self.structure_button)
        structure.addStretch()
        self.type_combo.currentIndexChanged.connect(self._sync_level_state)
        editor_layout.addLayout(structure)
        actions = QHBoxLayout()
        apply_button = QPushButton("应用文字")
        apply_button.clicked.connect(self.apply_text)
        self.merge_button = QPushButton("合并上一段")
        self.merge_button.clicked.connect(self.merge_previous)
        self.split_button = QPushButton("在光标处拆分")
        self.split_button.clicked.connect(self.split_block)
        up = QPushButton("上移")
        up.clicked.connect(lambda: self.move_block(-1))
        down = QPushButton("下移")
        down.clicked.connect(lambda: self.move_block(1))
        self.flag_button = QPushButton("标记错误")
        self.flag_button.clicked.connect(self.toggle_flag)
        for button in (apply_button, self.merge_button, self.split_button, up, down, self.flag_button):
            actions.addWidget(button)
        editor_layout.addLayout(actions)
        text_layout.addWidget(editor_card, 2)
        splitter.addWidget(text_area)
        splitter.setSizes([560, 640])
        layout.addWidget(splitter, 1)
        QShortcut(QKeySequence.StandardKey.Undo, self, self.undo_stack.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, self.undo_stack.redo)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_current)
        self._refresh_history_buttons()

    def open_project(self, directory):
        try:
            store = ProjectStore.open(directory)
            project = store.load()
            pages = store.load_pages()
        except Exception as exc:
            QMessageBox.critical(self, "无法打开项目", str(exc))
            return False
        self.store, self.project = store, project
        self.pages = sorted(pages, key=lambda page: page.number)
        self.index = 0
        self.undo_stack.clear()
        self.title.setText(f"{project['title']} · OCR 校对")
        self.save_state.setText("已自动保存")
        self.export_button.setEnabled(True)
        self._load_page()
        return True

    def _page(self):
        return self.pages[self.index] if self.pages else None

    def _load_page(self):
        page = self._page()
        self.blocks.clear()
        self.editor.clear()
        self.editor.setEnabled(False)
        self.current_block_id = None
        if not page:
            self.page_label.setText("第 – 页")
            self.viewer.load("")
            return
        self.page_label.setText(f"第 {page.number} 页 / 共 {len(self.pages)} 页")
        self.previous_button.setEnabled(self.index > 0)
        self.next_button.setEnabled(self.index < len(self.pages) - 1)
        original = self.store.directory / (page.original_image or page.image)
        self.viewer.load(original)
        self._rebuild()

    def _rebuild(self):
        page = self._page()
        if not page:
            return
        selected = self.current_block_id
        self.blocks.blockSignals(True)
        self.blocks.clear()
        threshold = self.settings_manager.settings().low_confidence
        low_count = 0
        for block in sorted(page.blocks, key=lambda item: item.reading_order):
            label = LABELS.get(block.block_type, block.block_type)
            flag = "  ⚑" if block.flagged else ""
            exclusion = "（不导出）" if block.excluded else ""
            number = f"{block.reading_order + 1:02d}"
            item = QListWidgetItem(f"{number}  [{label}] {block.text[:100]}{flag}{exclusion}")
            item.setData(Qt.ItemDataRole.UserRole, block.id)
            if block.flagged:
                item.setForeground(QColor("#c34d3b"))
            elif block.confidence < threshold:
                item.setForeground(QColor("#b57825"))
                low_count += 1
            item.setToolTip(f"置信度 {block.confidence:.3f}\n坐标 {[round(v) for v in block.rect]}")
            self.blocks.addItem(item)
        self.blocks.blockSignals(False)
        display = inverse_display_blocks(page)
        self.viewer.page_image.set_blocks(display)
        self.low_count.setText(f"{low_count} 个低置信度" if low_count else "无低置信度")
        if selected:
            for row in range(self.blocks.count()):
                if self.blocks.item(row).data(Qt.ItemDataRole.UserRole) == selected:
                    self.blocks.setCurrentRow(row)
                    break

    def _selected(self, current, previous):
        if not current:
            return
        block_id = current.data(Qt.ItemDataRole.UserRole)
        page = self._page()
        block = next((item for item in page.blocks if item.id == block_id), None)
        if not block:
            return
        self.current_block_id = block_id
        self.viewer.page_image.select(block_id)
        self.editor.setEnabled(True)
        self.editor.setPlainText(block.text)
        self.editor.setFocus()
        label = LABELS.get(block.block_type, block.block_type)
        self.editor_type.setText(f"{label} · 第 {block.page_number} 页 · 顺序 {block.reading_order + 1}")
        self.confidence.setText(f"置信度 {block.confidence:.1%}")
        self.flag_button.setText("取消错误标记" if block.flagged else "标记错误")
        type_index = self.type_combo.findData(block.block_type)
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)
        level_index = self.level_combo.findData(max(1, block.chapter_level))
        if level_index >= 0:
            self.level_combo.setCurrentIndex(level_index)
        self._sync_level_state()

    def _clicked_image(self, x, y):
        page = self._page()
        if not page:
            return
        candidates = []
        for block in inverse_display_blocks(page):
            left, top, right, bottom = block.rect
            if left <= x <= right and top <= y <= bottom:
                candidates.append(block)
        if not candidates:
            return
        block = min(candidates, key=lambda item: item.height)
        for row in range(self.blocks.count()):
            if self.blocks.item(row).data(Qt.ItemDataRole.UserRole) == block.id:
                self.blocks.setCurrentRow(row)
                break

    def _push(self, before, label):
        page = self._page()
        after = copy.deepcopy(page.blocks)
        command = BlocksCommand(page, before, after, self._changed, label)
        self.undo_stack.push(command)

    def _changed(self):
        self.save_current()
        self._rebuild()
        page = self._page()
        if page and self.current_block_id:
            block = next((item for item in page.blocks if item.id == self.current_block_id), None)
            if block:
                self.editor.setPlainText(block.text)

    def apply_text(self):
        page = self._page()
        if not page or not self.current_block_id:
            return
        block = next((item for item in page.blocks if item.id == self.current_block_id), None)
        if not block or block.text == self.editor.toPlainText():
            return
        before = copy.deepcopy(page.blocks)
        block.text = self.editor.toPlainText()
        block.manual_type = True
        self._push(before, "修改识别文字")

    def _sync_level_state(self):
        self.level_combo.setEnabled(self.type_combo.currentData() == "heading")

    def apply_structure(self):
        page = self._page()
        if not page or not self.current_block_id:
            return
        block = next((item for item in page.blocks if item.id == self.current_block_id), None)
        if not block:
            return
        block_type = self.type_combo.currentData()
        level = self.level_combo.currentData() if block_type == "heading" else 0
        if block.block_type == block_type and block.chapter_level == level:
            return
        before = copy.deepcopy(page.blocks)
        block.block_type = block_type
        block.chapter_level = level
        block.manual_type = True
        if block_type not in ("header", "footer", "page_number"):
            block.excluded = False
        self._push(before, "调整文字结构与章节层级")

    def merge_previous(self):
        page = self._page()
        if not page or not self.current_block_id:
            return
        ordered = sorted(page.blocks, key=lambda item: item.reading_order)
        position = next((index for index, item in enumerate(ordered) if item.id == self.current_block_id), -1)
        if position <= 0:
            return
        previous, current = ordered[position - 1], ordered[position]
        if (previous.block_type in ("heading", "table", "image", "formula") or
                current.block_type in ("table", "image", "formula")):
            QMessageBox.information(self, "无法合并", "标题、图片、表格或公式不能按正文段落合并。")
            return
        before = copy.deepcopy(page.blocks)
        separator = " " if previous.text[-1:].isascii() and previous.text[-1:].isalnum() else ""
        current.text = previous.text + separator + current.text
        current.manual_type = True
        page.blocks.remove(previous)
        for order, item in enumerate(sorted(page.blocks, key=lambda item: item.reading_order)):
            item.reading_order = order
        self._push(before, "合并段落")

    def split_block(self):
        page = self._page()
        if not page or not self.current_block_id:
            return
        cursor = self.editor.textCursor().position()
        current_text = self.editor.toPlainText()
        if cursor <= 0 or cursor >= len(current_text):
            QMessageBox.information(self, "拆分位置", "请先在文字编辑区把光标放到要拆分的位置。")
            return
        block = next((item for item in page.blocks if item.id == self.current_block_id), None)
        before = copy.deepcopy(page.blocks)
        first, second = current_text[:cursor].rstrip(), current_text[cursor:].lstrip()
        block.text = first
        block.manual_type = True
        clone = copy.deepcopy(block)
        clone.id = Block(page.number, "", 0, []).id
        clone.text = second
        clone.flagged = False
        clone.manual_type = True
        ordered = sorted(page.blocks, key=lambda item: item.reading_order)
        position = next(index for index, item in enumerate(ordered) if item.id == block.id)
        for item in ordered[position + 1:]:
            item.reading_order += 1
        clone.reading_order = block.reading_order + 1
        page.blocks.append(clone)
        page.blocks = sorted(page.blocks, key=lambda item: item.reading_order)
        self.current_block_id = block.id
        self._push(before, "拆分段落")

    def move_block(self, direction):
        page = self._page()
        ordered = sorted(page.blocks, key=lambda item: item.reading_order)
        position = next((index for index, item in enumerate(ordered) if item.id == self.current_block_id), -1)
        target = position + direction
        if position < 0 or target < 0 or target >= len(ordered):
            return
        before = copy.deepcopy(page.blocks)
        ordered[position].reading_order, ordered[target].reading_order = (
            ordered[target].reading_order, ordered[position].reading_order)
        self._push(before, "调整阅读顺序")

    def toggle_flag(self):
        page = self._page()
        block = next((item for item in page.blocks if item.id == self.current_block_id), None) if page else None
        if not block:
            return
        before = copy.deepcopy(page.blocks)
        block.flagged = not block.flagged
        self._push(before, "标记校对状态")

    def _refresh_history_buttons(self):
        self.undo_button.setEnabled(self.undo_stack.canUndo())
        self.redo_button.setEnabled(self.undo_stack.canRedo())
        self.undo_button.setToolTip(self.undo_stack.undoText() or "没有可撤销的操作")
        self.redo_button.setToolTip(self.undo_stack.redoText() or "没有可重做的操作")

    def save_current(self):
        page = self._page()
        if not page or not self.store:
            return
        try:
            self.store.save_page(page)
            self.save_state.setText("已自动保存")
        except Exception as exc:
            self.save_state.setText("保存失败")
            QMessageBox.critical(self, "保存失败", str(exc))

    def change_page(self, direction):
        new_index = self.index + direction
        if 0 <= new_index < len(self.pages):
            self.save_current()
            self.index = new_index
            self.undo_stack.clear()
            self._load_page()

    def export(self):
        if not self.store:
            return
        self.save_current()
        try:
            path = export_project(str(self.store.directory))
            validation = validate_epub(path)
            external = epubcheck(path) if validation["ok"] else {"ok": None, "message": ""}
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        self.save_state.setText("已导出")
        box = QMessageBox(self)
        box.setWindowTitle("导出完成")
        box.setText(f"校对后的 EPUB 已生成。\n\n{path}\n\n结构验证："
                    + ("通过" if validation["ok"] else "未通过")
                    + (f"\nEPUBCheck：{'通过' if external['ok'] else '未通过'}"
                       if external["ok"] is not None else
                       (f"\n{external['message']}" if external["message"] else "")))
        if validation["errors"]:
            box.setDetailedText("\n".join(validation["errors"]))
        open_button = box.addButton("打开文件夹", QMessageBox.ButtonRole.ActionRole)
        box.addButton("关闭", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() == open_button:
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
        self.completed.emit()

