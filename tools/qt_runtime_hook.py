from __future__ import annotations

import ctypes
import os
import sys


root = getattr(sys, "_MEIPASS", None)
if root:
    pyside = os.path.join(root, "PySide6")
    shiboken = os.path.join(root, "shiboken6")
    for directory in (root, pyside, shiboken):
        if os.path.isdir(directory):
            os.add_dll_directory(directory)
    for relative in (
        os.path.join("shiboken6", "shiboken6.abi3.dll"),
        os.path.join("PySide6", "Qt6" + "Core.dll"),
        os.path.join("PySide6", "pyside6.abi3.dll"),
    ):
        path = os.path.join(root, relative)
        if os.path.exists(path):
            ctypes.WinDLL(path)
