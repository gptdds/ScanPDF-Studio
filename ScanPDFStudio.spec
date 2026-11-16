import os
from PyInstaller.utils.hooks import (collect_all, collect_dynamic_libs,
                                     copy_metadata, get_package_paths)
from pathlib import Path

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

datas, binaries, hiddenimports = [], [], []
for package in ("paddle", "paddlex", "paddleocr", "cv2", "lxml", "opencc"):
    try:
        package_datas, package_binaries, package_hidden = collect_all(package)
        datas += package_datas
        binaries += package_binaries
        hiddenimports += package_hidden
    except Exception:
        pass
hiddenimports += [
    "scanpdf", "fitz", "PIL.Image", "paddle.base", "paddle.inference",
    "paddle.base.core", "paddleocr", "paddlex", "shapely", "pyclipper",
    "ujson", "crc32c", "filelock", "yaml", "prettytable", "pydantic",
    "paddle.dataset", "paddle.text",
]
_unsafe_hidden = ("paddle.jit.sot",)
hiddenimports = [
    name for name in hiddenimports
    if not name.startswith(_unsafe_hidden)
]
datas += [("tools/epubcheck", "tools/epubcheck")]
if Path("resources").exists():
    datas += [("resources", "resources")]
datas += copy_metadata("paddlex", recursive=True)
for distribution in (
    "imagesize", "opencv-contrib-python", "pyclipper", "pypdfium2",
    "python-bidi", "shapely", "opencc-python-reimplemented",
):
    datas += copy_metadata(distribution)

_, _paddle_package = get_package_paths("paddle")
for _dll in (Path(_paddle_package) / "libs").glob("*.dll"):
    binaries.append((str(_dll), "paddle/libs"))

a = Analysis(
    ["src\\scanpdf\\packaging_entry.py"], pathex=["src"],
    binaries=binaries, datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "paddle.jit.sot"],
    noarchive=False,
)
_poppler_icu = {"icuuc.dll", "icudt78.dll"}
a.binaries = [
    item for item in a.binaries
    if Path(item[0]).name.lower() not in _poppler_icu
]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="ScanPDFStudio", debug=False, strip=False,
    upx=False, console=False, icon="resources/icon.ico",
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, name="ScanPDFStudio",
)

