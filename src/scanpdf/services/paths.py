import os
import atexit
import string
import subprocess
import sys
from pathlib import Path


def data_dir():
    override = os.environ.get("SCANPDF_DATA_DIR")
    candidates = [Path(override)] if override else [
        Path(os.environ.get("APPDATA", Path.home())) / "ScanPDFStudio",
        Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ScanPDFStudio",
        Path.home() / "Documents" / "ScanPDFStudio",
        (Path(sys.executable).parent if getattr(sys, "frozen", False)
         else Path(__file__).resolve().parents[3]) / "ScanPDFData",
        Path.cwd() / "ScanPDFData",
    ]
    last_error = None
    for root in candidates:
        try:
            root.mkdir(parents=True, exist_ok=True)
            probe = root / "write-test.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return root
        except OSError as exc:
            last_error = exc
    raise OSError(f"无法创建本地数据目录: {last_error}")


def bundled_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))


def model_dir():
    bundled = bundled_root() / "models"
    if bundled.is_dir():
        return bundled
    target = ascii_data_dir() / "models"
    target.mkdir(exist_ok=True)
    return target


_ASCII_ROOTS = {}


def _is_ascii(path):
    return all(ord(character) < 128 for character in str(path))


def ascii_data_dir():
    root = data_dir()
    if _is_ascii(root):
        return root
    key = str(root.resolve())
    if key in _ASCII_ROOTS:
        return _ASCII_ROOTS[key]
    if os.name == "nt":
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:\\")
            try:
                if not drive.exists():
                    continue
                target = Path(os.path.realpath(drive))
                if root.is_relative_to(target):
                    mapped = drive / root.relative_to(target)
                    if _is_ascii(mapped) and mapped.exists():
                        _ASCII_ROOTS[key] = mapped
                        return mapped
            except OSError:
                continue
        for letter in reversed(string.ascii_uppercase[6:]):
            drive = Path(f"{letter}:\\")
            if drive.exists():
                continue
            try:
                result = subprocess.run(
                    ["subst", f"{letter}:", key], capture_output=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if result.returncode == 0 and drive.exists():
                    _ASCII_ROOTS[key] = drive
                    atexit.register(_release_subst, drive)
                    return drive
            except OSError:
                continue
    return root


def _release_subst(drive):
    try:
        subprocess.run(["subst", str(drive)[:2], "/D"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError:
        pass

