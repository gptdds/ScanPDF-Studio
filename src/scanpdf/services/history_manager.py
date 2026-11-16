import json
import sqlite3
from datetime import datetime
from pathlib import Path

from scanpdf.services.paths import data_dir


class HistoryManager:
    def __init__(self):
        self.path = data_dir() / "history.sqlite3"
        with self.connect() as database:
            database.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
                source TEXT NOT NULL, output TEXT, project TEXT UNIQUE NOT NULL,
                pages INTEGER DEFAULT 0, mean_confidence REAL DEFAULT 0,
                low_confidence INTEGER DEFAULT 0, status TEXT NOT NULL,
                updated TEXT NOT NULL)""")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def upsert(self, record):
        pages = record.get("pages", record.get("total_pages", 0))
        with self.connect() as database:
            database.execute("""INSERT INTO jobs
                (title,source,output,project,pages,mean_confidence,low_confidence,status,updated)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(project) DO UPDATE SET title=excluded.title, source=excluded.source,
                output=excluded.output, pages=excluded.pages,
                mean_confidence=excluded.mean_confidence, low_confidence=excluded.low_confidence,
                status=excluded.status, updated=excluded.updated""", (
                record["title"], record["source"], record.get("output", ""),
                record["project"], pages,
                record.get("mean_confidence", 0), record.get("low_confidence", 0),
                record["status"], datetime.now().isoformat(timespec="seconds")))

    def records(self, limit=100):
        with self.connect() as database:
            database.row_factory = sqlite3.Row
            return [dict(row) for row in database.execute(
                "SELECT * FROM jobs ORDER BY updated DESC LIMIT ?", (limit,))]

    def delete(self, project):
        with self.connect() as database:
            database.execute("DELETE FROM jobs WHERE project=?", (project,))

