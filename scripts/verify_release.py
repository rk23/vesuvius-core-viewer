"""Verify the explicit distribution boundary without third-party Python packages."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from umbilicus_viewer.schema import read_scene  # noqa: E402

SCROLLS = {"PHerc0175A", "PHerc0175B", "PHerc0191", "PHerc0257", "PHerc0800", "PHerc1218", "PHerc1667"}
SOURCE_FILES = {
    ".gitignore", ".gitattributes", ".github/workflows/check.yml", "AGENTS.md", "README.md", "ATTRIBUTION.md", "LICENSE",
    "pyproject.toml", "uv.lock", "index.html", "app.js", "viewer.js", "style.css", "docs/RELEASE.md",
    "data/README.md", "data/catalog.json", "data/manifest.json", "vendor/manifest.json",
    "vendor/three.module.js", "vendor/OrbitControls.js", "licenses/THREE.txt", "licenses/CT-DATA.txt",
    "licenses/HERCULANEUM-UMBILICI.txt", "umbilicus_viewer/__init__.py", "umbilicus_viewer/__main__.py",
    "umbilicus_viewer/schema.py", "umbilicus_viewer/builder.py", "scripts/verify_release.py",
    "scripts/export_site.py", "tests/test_builder.py", "tests/test_release.py", "tests/browser_smoke.py",
}
DATA_FILES = {f"data/{kind}/{s}{suffix}" for s in SCROLLS
              for kind, suffix in [("scenes", ".json.gz"), ("axes", ".json")]}
ALLOWED_FILES = SOURCE_FILES | DATA_FILES
IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "node_modules",
                "playwright-report", "test-results"}


def release_files(root: Path):
    for directory, folders, files in root.walk():
        relative = directory.relative_to(root)
        for name in folders + files:
            if (directory / name).is_symlink():
                raise ValueError(f"Symlink is outside the distribution boundary: {relative / name}")
        folders[:] = [f for f in folders if f not in IGNORED_DIRS and not (relative == Path("data") and f == "local")]
        for name in files:
            if name == ".DS_Store":
                continue
            yield directory / name


def verify(root: Path = ROOT):
    actual = {p.relative_to(root).as_posix() for p in release_files(root)}
    if actual != ALLOWED_FILES:
        raise ValueError(f"File boundary differs: extra={sorted(actual - ALLOWED_FILES)}, "
                         f"missing={sorted(ALLOWED_FILES - actual)}")
    if any((root / rel).stat().st_size >= 100_000_000 for rel in actual):
        raise ValueError("A release file exceeds 100 MB")
    manifest = json.loads((root / "data/manifest.json").read_text())
    if {f["path"] for f in manifest["files"]} != DATA_FILES | {"data/catalog.json"}:
        raise ValueError("Data manifest differs from the allowlisted files")
    for name in ["data/manifest.json", "vendor/manifest.json"]:
        for f in json.loads((root / name).read_text())["files"]:
            if f["path"] not in actual:
                raise ValueError("Manifest references a file outside the release")
            if hashlib.sha256((root / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
                raise ValueError(f"Checksum mismatch: {f['path']}")
    catalog = json.loads((root / "data/catalog.json").read_text())
    if len(catalog["scenes"]) != len(SCROLLS) or {s["id"] for s in catalog["scenes"]} != SCROLLS:
        raise ValueError("Scene catalog does not match the seven prepared scrolls")
    total_bytes = 0
    for entry in catalog["scenes"]:
        sid = entry["id"]
        if entry["scene"] != f"data/scenes/{sid}.json.gz" or entry["axis"] != f"data/axes/{sid}.json":
            raise ValueError("Unexpected scene or axis path")
        scene = read_scene(root / entry["scene"])
        if scene["provenance"] != entry["provenance"] or scene["z_range"] != entry["z_range"]:
            raise ValueError(f"Catalog and scene metadata disagree: {sid}")
        axis = json.loads((root / entry["axis"]).read_text())
        if set(axis) != {"control_points"} or not axis["control_points"]:
            raise ValueError("Axis files may contain only control points")
        for p in axis["control_points"]:
            if set(p) != {"x", "y", "z"}:
                raise ValueError("Unexpected axis control-point fields")
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in p.values()):
                raise ValueError("Axis coordinates must be numbers")
        total_bytes += (root / entry["scene"]).stat().st_size
    return {"files": len(actual), "scenes": len(catalog["scenes"]), "scene_bytes": total_bytes}


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), indent=2))
    except (ValueError, OSError) as error:
        raise SystemExit(str(error)) from error
