"""Copy only verified browser assets and prepared scenes into a fresh static-site directory."""

import argparse
import shutil
from pathlib import Path

from verify_release import ROOT, verify

STATIC = {"index.html", "app.js", "viewer.js", "style.css", "LICENSE", "ATTRIBUTION.md"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verify()
    destination = args.output.resolve()
    if destination.exists():
        parser.error("Output must be a new directory")
    paths = set(STATIC)
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "vendor").iterdir() if p.is_file())
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "licenses").iterdir() if p.is_file())
    paths.update({"data/catalog.json", "data/manifest.json", "data/README.md"})
    paths.update(f"data/scenes/{p.name}" for p in (ROOT / "data/scenes").iterdir())
    paths.update(f"data/axes/{p.name}" for p in (ROOT / "data/axes").iterdir())
    for relative in sorted(paths):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    print(f"Exported {len(paths)} files to {destination}")


if __name__ == "__main__":
    main()
