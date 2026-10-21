# Repository guidelines

## Scope

Vesuvius Core Viewer is a standalone browser tool for visualizing the centers of CT-scanned papyrus
scrolls. Keep contributions focused on CT display, center axes, portable scene preparation, and
accessibility. The viewer must work from a plain HTTP server without accounts or a backend.

## Structure

- `index.html`, `app.js`, `viewer.js`, `style.css`: browser UI, scene loading, and Three.js display.
- `umbilicus_viewer/`: optional Python scene preparation and strict format validation.
- `data/scenes/`, `data/axes/`, `data/catalog.json`: prepared visualization data and public provenance.
- `vendor/`, `licenses/`, `ATTRIBUTION.md`: pinned third-party dependencies and separate data terms.
- `scripts/`: verification and an allowlisted static-site export.
- `tests/`: synthetic coordinate checks and release checks.

## Changes and validation

Inspect Git status before editing and preserve concurrent work. Python requires 3.12+, uses four
spaces, and follows Ruff's 110-character limit. JavaScript is native browser modules; no Node build
step is required. Keep scene keys explicit and synchronized between Python and JavaScript validation.

Run `uv run pytest`, `uv run ruff check .`, and `python3 scripts/verify_release.py`. Browser changes
also need the documented smoke test and a visual check. New data must retain its source attribution,
coordinate frame, license, and manifest checksum. Update manifests deliberately after inspecting changes.

## Data boundaries

Use `data/local/` for personal scenes and `dist/` for exports; both are ignored. Release only the
documented scene schema. Keep arbitrary attachments, machine paths, credentials, private annotations,
and unrelated project files out of the repository and its Git history. Do not add symlinks to external
checkouts. Viewer code is MIT; CT data retains CC BY-NC 4.0. Preserve every third-party notice.
