import json
import os
import shutil
import uuid
from pathlib import Path

from scanpdf.models import Page, Settings, to_dict
from scanpdf.services.paths import data_dir


class ProjectStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / "assets").mkdir(exist_ok=True)
        (self.directory / "pages").mkdir(exist_ok=True)
        (self.directory / "raw").mkdir(exist_ok=True)
        self.file = self.directory / "project.json"

    @classmethod
    def create(cls, pdf_path, settings, output_path=None, data_root=None):
        root = Path(data_root or data_dir()) / "projects"
        root.mkdir(parents=True, exist_ok=True)
        return cls(root / uuid.uuid4().hex).initialize(pdf_path, settings, output_path)

    def initialize(self, pdf_path, settings, output_path=None):
        data = {
            "book_id": f"urn:uuid:{uuid.uuid4()}", "title": Path(pdf_path).stem,
            "author": "未知", "pdf": str(Path(pdf_path).resolve()),
            "output": str(Path(output_path).resolve()) if output_path else "",
            "settings": to_dict(settings), "total_pages": 0, "status": "ready",
            "created": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "directory": str(self.directory),
        }
        self.save(data)
        return data

    def load(self):
        return json.loads(self.file.read_text(encoding="utf-8"))

    def save(self, data):
        temporary = self.file.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.file)

    def save_page(self, page, raw=None):
        temporary = self.directory / "pages" / f"{page.number:06d}.tmp"
        temporary.write_text(json.dumps(to_dict(page), ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.directory / "pages" / f"{page.number:06d}.json")
        if raw is not None:
            (self.directory / "raw" / f"{page.number:06d}.json").write_text(
                json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    def load_pages(self):
        pages = []
        for path in sorted((self.directory / "pages").glob("*.json")):
            try:
                pages.append(Page.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, ValueError, TypeError, KeyError):
                continue
        return pages

    def load_page(self, number):
        path = self.directory / "pages" / f"{number:06d}.json"
        if not path.exists():
            return None
        return Page.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def completed_numbers(self):
        return {page.number for page in self.load_pages()}

    def remove_incomplete_temporary_files(self):
        for folder in ("pages", "raw"):
            for path in (self.directory / folder).glob("*.tmp"):
                path.unlink(missing_ok=True)

    @classmethod
    def open(cls, directory):
        store = cls(directory)
        if not store.file.exists():
            raise FileNotFoundError("项目文件不存在。")
        store.remove_incomplete_temporary_files()
        return store

    def delete(self):
        if self.directory.parent.name != "projects":
            raise ValueError("拒绝删除不在 ScanPDF 项目目录中的文件夹。")
        shutil.rmtree(self.directory)

