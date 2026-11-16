import json
from pathlib import Path

import pytest

from fixtures import make_scanned_pdf
from scanpdf.core.pdf_loader import PDFDocument
from scanpdf.models import Block, Page, Settings, rectangle
from scanpdf.pipeline import Pipeline
from scanpdf.services.checkpoint_manager import ProjectStore


class FakeEngine:
    def __init__(self, settings, progress=None, cancel=None):
        self.settings = settings

    def orientation(self, image):
        return 0

    def recognize(self, image, page_number):
        blocks = [
            Block(page_number, f"第{page_number}页标题", 0.99,
                  rectangle(180, 80, 380, 120), block_type="body"),
            Block(page_number, "这是用于断点恢复测试的中文段落。", 0.94,
                  rectangle(80, 160, 500, 200), block_type="body"),
            Block(page_number, str(page_number + 10), 0.99,
                  rectangle(270, 760, 290, 780), block_type="body"),
        ]
        return blocks, {"rec_texts": [block.text for block in blocks]}


def test_checkpoint_resume_processes_only_missing_pages(tmp_path, monkeypatch):
    pdf_path = make_scanned_pdf(tmp_path / "resume.pdf")
    root = tmp_path / "projects"
    store = ProjectStore(root / "project-a")
    project = store.initialize(pdf_path, Settings(orientation=False, keep_images=False), tmp_path / "out.epub")
    project["total_pages"] = 5
    store.save(project)
    first = Page(1, 100, 100, [Block(1, "已存在", 1.0, rectangle(1, 1, 5, 5))])
    store.save_page(first, {"kept": True})
    assert json.loads((store.directory / "raw" / "000001.json").read_text(encoding="utf-8"))["kept"]
    monkeypatch.setattr("scanpdf.pipeline.PaddleEngine", FakeEngine)
    messages = []
    pipeline = Pipeline(str(store.directory), lambda value, message: messages.append(message),
                        lambda: False, lambda: False)
    pages = pipeline.run()
    assert sorted(page.number for page in pages) == [1, 2, 3, 4, 5]
    assert pages[0].blocks[0].text == "已存在"
    assert (store.directory / "raw" / "000002.json").exists()
    assert json.loads((store.directory / "project.json").read_text(encoding="utf-8"))["status"] == "complete"


def test_failed_page_is_recorded_not_silently_skipped(tmp_path, monkeypatch):
    pdf_path = make_scanned_pdf(tmp_path / "failure.pdf")
    store = ProjectStore(tmp_path / "projects" / "project-b")
    project = store.initialize(pdf_path, Settings(orientation=False, keep_images=False), tmp_path / "out.epub")
    project["total_pages"] = 5
    store.save(project)

    class FailingEngine(FakeEngine):
        def recognize(self, image, page_number):
            if page_number == 2:
                raise RuntimeError("模拟识别失败")
            return super().recognize(image, page_number)

    monkeypatch.setattr("scanpdf.pipeline.PaddleEngine", FailingEngine)
    Pipeline(str(store.directory), lambda value, message: None,
             lambda: False, lambda: False).run()
    pages = {page.number: page for page in store.load_pages()}
    assert pages[2].warnings
    assert "模拟识别失败" in pages[2].warnings[0]
    assert pages[1].blocks and pages[3].blocks


def test_history_and_project_delete_guard(tmp_path):
    from scanpdf.services.history_manager import HistoryManager
    import scanpdf.services.history_manager as module
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(module, "data_dir", lambda: tmp_path)
    history = HistoryManager()
    record = {"title": "书", "source": "C:/a.pdf", "output": "", "project": "C:/project",
              "pages": 2, "mean_confidence": 0.91, "low_confidence": 1, "status": "complete"}
    history.upsert(record)
    assert history.records()[0]["title"] == "书"
    history.upsert({"title": "书二", "source": "C:/b.pdf", "project": "C:/project-2",
                    "total_pages": 5, "mean_confidence": 0.9,
                    "low_confidence": 0, "status": "exported"})
    assert {item["project"]: item["pages"] for item in history.records()} == {
        "C:/project": 2, "C:/project-2": 5}
    history.delete("C:/project")
    assert [item["project"] for item in history.records()] == ["C:/project-2"]
    monkeypatch.undo()


def test_batch_queue_processes_sequentially(tmp_path, monkeypatch):
    from scanpdf.services.task_queue import BatchQueue

    class FakePipeline:
        def __init__(self, directory, progress, cancelled, paused):
            self.directory = directory
            self.progress = progress

        def run(self):
            self.progress(100, "完成")

    monkeypatch.setattr("scanpdf.services.task_queue.Pipeline", FakePipeline)
    monkeypatch.setattr("scanpdf.services.task_queue.export_project",
                        lambda directory, output=None: Path(output))
    queue = BatchQueue()
    queue.set_settings(Settings(orientation=False, keep_images=False))
    queue.add([tmp_path / "one.pdf", tmp_path / "two.pdf"], Settings(),
              output_dir=tmp_path)
    assert queue.start()
    queue.wait(5)
    jobs = queue.snapshot()
    assert [job["status"] for job in jobs] == ["已导出", "已导出"]
    assert all(Path(job["output"]).parent == tmp_path for job in jobs)

