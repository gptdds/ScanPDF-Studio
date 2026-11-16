import json
import time
import traceback
from pathlib import Path

from scanpdf.core.epub_builder import build_epub
from scanpdf.core.image_extractor import retain_regions
from scanpdf.core.image_preprocessor import preprocess
from scanpdf.core.layout_analyzer import analyze, clean_repeated_margins
from scanpdf.core.ocr_engine import PaddleEngine
from scanpdf.core.paragraph_builder import build_paragraphs
from scanpdf.core.pdf_loader import PDFDocument
from scanpdf.models import Page, Settings, to_dict
from scanpdf.services.checkpoint_manager import ProjectStore
from scanpdf.services.history_manager import HistoryManager


class Cancelled(Exception):
    pass


class Pipeline:
    def __init__(self, project_directory, progress, cancelled, paused, page_ready=None):
        self.store = ProjectStore.open(project_directory)
        self.project = self.store.load()
        self.settings = Settings(**self.project["settings"])
        self.progress = progress
        self.cancelled = cancelled
        self.paused = paused
        self.page_ready = page_ready
        self.engine = None

    def _check(self):
        if self.cancelled():
            raise Cancelled()
        while self.paused():
            self.progress(0, "已暂停 · 当前页已完成并保存")
            time.sleep(0.25)
            if self.cancelled():
                raise Cancelled()

    def run(self):
        self.progress(0, "正在打开 PDF…")
        self.store.remove_incomplete_temporary_files()
        with PDFDocument(self.project["pdf"]) as pdf:
            self.project["total_pages"] = pdf.page_count
            self.project["status"] = "processing"
            self.store.save(self.project)
            HistoryManager().upsert({**self.project, "source": self.project["pdf"],
                                     "project": str(self.store.directory), "status": "processing"})
            done = self.store.completed_numbers()
            pages = {page.number: page for page in self.store.load_pages()}
            missing = [number for number in range(1, pdf.page_count + 1) if number not in done]
            if missing:
                self.engine = PaddleEngine(
                    self.settings, lambda message: self.progress(0, message), self.cancelled)
            started = time.monotonic()
            processed_this_run = 0
            for number in missing:
                self._check()
                page_started = time.monotonic()
                self.progress(self._percent(number - 1, pdf.page_count),
                              f"正在识别第 {number} / {pdf.page_count} 页")
                try:
                    image = pdf.render(number, self.settings.dpi)
                    original = image.copy()
                    rotation = self.engine.orientation(original) if self.settings.orientation else 0
                    processed, transform, skew = preprocess(original, self.settings, rotation)
                    blocks, raw = self.engine.recognize(processed, number)
                    page = Page(number, processed.shape[1], processed.shape[0], blocks,
                                warnings=[], rotation=rotation, skew=skew,
                                transform=transform.tolist(), seconds=time.monotonic() - page_started)
                    page.original_image = f"pages/original-{number:05d}.png"
                    from PIL import Image
                    Image.fromarray(original).save(self.store.directory / page.original_image)
                    page.image = f"pages/processed-{number:05d}.png"
                    Image.fromarray(processed).save(self.store.directory / page.image)
                    analyze(page, self.settings)
                    retain_regions(processed, page, self.store.directory, self.settings, self.engine)
                    analyze(page, self.settings)
                    if not any(block.text.strip() for block in page.blocks if block.block_type == "body"):
                        page.warnings.append("本页未识别到文字；已保留空页并记录原始 OCR 结果，请在校对台检查。")
                    self.store.save_page(page, raw)
                    pages[number] = page
                    processed_this_run += 1
                    if self.page_ready:
                        self.page_ready(number)
                except Cancelled:
                    if "page" in locals():
                        self.store.save_page(page, raw)
                    raise
                except Exception as exc:
                    failed = Page(number, 0, 0, [], warnings=[f"第 {number} 页处理失败: {exc}"])
                    self.store.save_page(failed)
                    pages[number] = failed
                    if self.page_ready:
                        self.page_ready(number)
                    self.progress(self._percent(number, pdf.page_count),
                                  f"第 {number} 页失败，已记录并可续跑")
                elapsed = time.monotonic() - started
                average = elapsed / max(1, processed_this_run)
                remaining = sum(1 for item in range(number, pdf.page_count + 1)
                                if item not in pages and item not in done)
                self.progress(self._percent(number, pdf.page_count),
                              f"已完成第 {number} / {pdf.page_count} 页 · 预计剩余 {self._duration(average * remaining)}")
            all_pages = [pages[number] for number in sorted(pages)]
            clean_repeated_margins(all_pages, self.settings)
            for page in all_pages:
                self.store.save_page(page)
            self.project["status"] = "complete"
            self.project["error_pages"] = [page.number for page in all_pages if page.warnings and not page.blocks]
            self.store.save(self.project)
            scores = [block.confidence for page in all_pages for block in page.blocks
                      if block.text.strip() and block.block_type != "image"]
            low = sum(score < self.settings.low_confidence for score in scores)
            HistoryManager().upsert({**self.project, "source": self.project["pdf"],
                                     "project": str(self.store.directory),
                                     "output": self.project.get("output", ""),
                                     "mean_confidence": sum(scores) / len(scores) if scores else 0,
                                     "low_confidence": low, "status": "complete"})
            self.progress(100, "识别完成，可进入校对工作台。")
            return all_pages

    @staticmethod
    def _percent(done, total):
        return int(100 * done / max(1, total))

    @staticmethod
    def _duration(seconds):
        seconds = max(0, int(seconds))
        return f"{seconds // 60} 分 {seconds % 60} 秒" if seconds >= 60 else f"{seconds} 秒"


def export_project(project_directory, output=None):
    store = ProjectStore.open(project_directory)
    project = store.load()
    settings = Settings(**project["settings"])
    pages = store.load_pages()
    paragraphs = build_paragraphs(pages, settings)
    destination = Path(output or project.get("output") or
                       (Path.home() / "Desktop" / f"{project['title']}.epub"))
    build_epub(project, paragraphs, destination, settings)
    project["output"] = str(destination)
    store.save(project)
    scores = [block.confidence for page in pages for block in page.blocks if block.text.strip()]
    HistoryManager().upsert({**project, "source": project["pdf"], "project": str(store.directory),
                             "output": str(destination), "mean_confidence":
                             sum(scores) / len(scores) if scores else 0, "status": "exported"})
    return destination
