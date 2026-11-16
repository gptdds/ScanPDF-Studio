import threading
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from scanpdf.models import Settings
from scanpdf.pipeline import Cancelled, Pipeline, export_project
from scanpdf.services.checkpoint_manager import ProjectStore
from scanpdf.services.paths import data_dir


class BatchQueue(QObject):
    changed = Signal()
    message = Signal(str)

    def __init__(self, guard=None, parent=None):
        super().__init__(parent)
        self.guard = guard
        self._jobs = []
        self._lock = threading.Lock()
        self._thread = None
        self._stop = threading.Event()
        self._cancel = threading.Event()
        self._pause = threading.Event()
        self._next_id = 1
        self._settings = vars(Settings()).copy()

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def snapshot(self):
        with self._lock:
            return [dict(job) for job in self._jobs]

    def add(self, paths, settings, output_dir=None):
        output_dir = Path(output_dir or Path.home() / "Desktop")
        with self._lock:
            for path in paths:
                path = Path(path).resolve()
                output = output_dir / f"{path.stem}.epub"
                self._jobs.append({
                    "id": self._next_id, "pdf": str(path), "title": path.stem,
                    "status": "等待中", "progress": 0, "message": "",
                    "project": "", "output": str(output), "error": "",
                })
                self._next_id += 1
        self.changed.emit()

    def start(self):
        if self.running:
            return False
        if self.guard and not self.guard():
            return False
        if not any(job["status"] == "等待中" for job in self.snapshot()):
            return False
        self._stop.clear()
        self._cancel.clear()
        self._pause.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ScanPDF-queue")
        self._thread.start()
        return True

    def _run(self):
        while not self._stop.is_set():
            self._wait_if_paused()
            if self._stop.is_set():
                break
            with self._lock:
                job = next((item for item in self._jobs if item["status"] == "等待中"), None)
                if job:
                    job["status"] = "处理中"
            if not job:
                break
            self.changed.emit()
            try:
                store = self._project(job)
                with self._lock:
                    job["project"] = str(store.directory)
                pipeline = Pipeline(
                    str(store.directory),
                    lambda value, message, identifier=job["id"]:
                    self._progress(identifier, value, message),
                    self._cancel.is_set, self._pause.is_set)
                pipeline.run()
                self._progress(job["id"], 100, "正在生成 EPUB…")
                output = export_project(str(store.directory), job["output"])
                with self._lock:
                    job["status"] = "已导出"
                    job["progress"] = 100
                    job["message"] = str(output)
            except Cancelled:
                with self._lock:
                    job["status"] = "已取消"
                    job["message"] = "已完成页面已保存"
                self._cancel.clear()
            except Exception as exc:
                with self._lock:
                    job["status"] = "失败"
                    job["error"] = str(exc)
                self.message.emit(f"{job['title']} 失败: {exc}")
            finally:
                self.changed.emit()
        self.changed.emit()

    def _project(self, job):
        root = data_dir() / "projects"
        root.mkdir(parents=True, exist_ok=True)
        from uuid import uuid4
        store = ProjectStore(root / uuid4().hex)
        settings = Settings(**self._settings)
        project = store.initialize(job["pdf"], settings, job["output"])
        project["title"] = job["title"]
        store.save(project)
        return store

    def _progress(self, identifier, value, message):
        with self._lock:
            job = next((item for item in self._jobs if item["id"] == identifier), None)
            if job:
                job["progress"] = value
                job["message"] = message
        self.changed.emit()

    def set_settings(self, settings):
        self._settings = vars(settings).copy()

    def _wait_if_paused(self):
        while self._pause.is_set() and not self._stop.is_set():
            threading.Event().wait(0.2)

    def toggle_pause(self):
        if self._pause.is_set():
            self._pause.clear()
            self.message.emit("队列已继续")
        else:
            self._pause.set()
            self.message.emit("当前页完成后暂停队列")
        self.changed.emit()

    @property
    def paused(self):
        return self._pause.is_set()

    def cancel_current(self):
        self._cancel.set()
        self.message.emit("当前任务将在当前页完成后取消")

    def stop(self):
        self._stop.set()
        self._cancel.set()
        self._pause.clear()
        with self._lock:
            for job in self._jobs:
                if job["status"] == "等待中":
                    job["status"] = "已取消"
        self.changed.emit()

    def clear(self):
        with self._lock:
            self._jobs = [job for job in self._jobs
                          if job["status"] in ("处理中", "等待中")]
        self.changed.emit()

    def wait(self, timeout=10):
        if self._thread:
            self._thread.join(timeout)

