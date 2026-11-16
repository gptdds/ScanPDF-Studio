from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

import pefile


root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
search_dirs = [root, root / "PySide6", root / "shiboken6"]
for directory in search_dirs:
    if directory.is_dir():
        os.add_dll_directory(str(directory))

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.LoadLibraryW.argtypes = [ctypes.c_wchar_p]
kernel32.LoadLibraryW.restype = ctypes.c_void_p
kernel32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
kernel32.GetProcAddress.restype = ctypes.c_void_p


def find_dll(name: str) -> str:
    for directory in search_dirs:
        candidate = directory / name
        if candidate.is_file():
            return str(candidate)
    return name


def load_dll(name: str) -> int:
    path = find_dll(name)
    handle = kernel32.LoadLibraryW(path)
    if not handle:
        error = ctypes.get_last_error()
        print(f"LOAD FAIL {name}: {path} winerror={error}")
    else:
        print(f"LOAD OK   {name}: {path}")
    return handle or 0


core_path = root / "PySide6" / ("Qt6" + "Core.dll")
pe = pefile.PE(str(core_path))
pe.parse_data_directories(
    directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
)

handles: dict[str, int] = {}
for entry in pe.DIRECTORY_ENTRY_IMPORT:
    dll = entry.dll.decode()
    if dll.lower().startswith("api-ms-"):
        continue
    handle = load_dll(dll)
    handles[dll.lower()] = handle
    for item in entry.imports:
        if not item.name:
            continue
        symbol = item.name.decode()
        if handle and not kernel32.GetProcAddress(handle, symbol.encode()):
            print(f"MISSING {dll}: {symbol}")

handle = kernel32.LoadLibraryW(str(core_path))
if handle:
    print("QtCore loaded")
else:
    print(f"QtCore failed winerror={ctypes.get_last_error()}")
