from __future__ import annotations

import ctypes
from pathlib import Path


def load(path: Path) -> None:
    try:
        ctypes.WinDLL(str(path), winmode=0x00000008)
        print(f"OK      {path}")
    except OSError as exc:
        print(f"FAILED  {path}")
        print(f"        winerror={exc.winerror} {exc.strerror}")
        raise


root = Path(__file__).resolve().parents[1] / "dist" / "ScanPDFStudio" / "_internal"
pyside = root / "PySide6"
shiboken = root / "shiboken6"

for directory in (root, pyside, shiboken):
    ctypes.windll.kernel32.SetDllDirectoryW(str(directory))

for dll in (
    shiboken / "shiboken6.abi3.dll",
    pyside / "Qt6Core.dll",
    pyside / "Qt6Gui.dll",
    pyside / "pyside6.abi3.dll",
):
    load(dll)
