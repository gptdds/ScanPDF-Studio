from __future__ import annotations

import sys
from pathlib import Path

import pefile


def import_names(path: Path) -> dict[str, set[str]]:
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
    )
    imports: dict[str, set[str]] = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        names = imports.setdefault(entry.dll.decode().lower(), set())
        for item in entry.imports:
            names.add(item.name.decode() if item.name else f"#{item.ordinal}")
    return imports


def export_names(path: Path) -> tuple[set[str], set[int]]:
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
    )
    names: set[str] = set()
    ordinals: set[int] = set()
    exports = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if exports:
        for symbol in exports.symbols:
            ordinals.add(symbol.ordinal)
            if symbol.name:
                names.add(symbol.name.decode())
    return names, ordinals


root = Path(sys.argv[1] if len(sys.argv) > 1 else "dist-qt-smoke/QtSmoke/_internal")
roots = (root, root / "PySide6", root / "shiboken6")
files = {path.name.lower(): path for path in root.rglob("*") if path.is_file()}
queue = [
    root / "PySide6" / ("Qt" + "Core.pyd"),
    root / "PySide6" / "pyside6.abi3.dll",
    root / "shiboken6" / "shiboken6.abi3.dll",
    root / "PySide6" / ("Qt" + "Gui.pyd"),
]
seen: set[Path] = set()

while queue:
    path = queue.pop(0)
    if path in seen or not path.exists():
        continue
    seen.add(path)
    print(f"AUDIT {path.relative_to(root)}")
    for dll, names in import_names(path).items():
        dependency = files.get(dll)
        if dependency is None:
            continue
        exports, ordinals = export_names(dependency)
        missing = [
            name
            for name in sorted(names)
            if (name.startswith("#") and int(name[1:]) not in ordinals)
            or (not name.startswith("#") and name not in exports)
        ]
        if missing:
            print(f"  MISSING {dll} in {dependency.relative_to(root)}:")
            for name in missing:
                print(f"    {name}")
        if dependency.suffix.lower() in {".dll", ".pyd"}:
            queue.append(dependency)

print(f"Audited {len(seen)} bundled binaries.")
