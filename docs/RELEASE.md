# Vesuvius Core Viewer release preparation

The release scope is the CT center viewer and its seven prepared scenes. The portable scene schema
allows only titles, coordinates, CT-derived point positions, CT image crops, cross-section outlines,
display settings, and public provenance. Axis files contain only coordinate control points. The
repository starts with its own Git history.

`scripts/verify_release.py` checks the file allowlist, all scene schemas, axis formats, data and vendor
checksums, file sizes, and absence of symlinks. This is a packaging check; the reference axes and CT
threshold display remain approximate. Additional files require a deliberate allowlist update.

## Checks

```sh
uv sync --extra build --group dev
uv run pytest
uv run ruff check .
node --check app.js
node --check viewer.js
python3 scripts/verify_release.py
```

For automated browser checks, install the optional test tool and its browser:

```sh
uv run --with playwright playwright install chromium
uv run --with playwright python tests/browser_smoke.py --output dist/browser-check
```

The smoke test serves this repository on a random loopback port, loads all seven scenes, exercises
slice/filter/view controls, switches datasets, checks a local-file import and an invalid import,
captures desktop and narrow-screen screenshots, and rejects browser errors or external requests.
Screenshots stay in the ignored output directory. Inspect them before publishing UI changes.

## Static distribution

```sh
python3 scripts/export_site.py dist/site
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist/site
```

The exporter includes only explicit application files, cataloged scenes and axes, checksums, and
license notices. It excludes local scene files. This folder can be served by any static host, with
`.gz` scenes served as ordinary gzip files or transparently decompressed by the host; the loader
detects the gzip header. Keep `ATTRIBUTION.md`, `LICENSE`, and `licenses/` with the site.

## GitHub Pages

The project site is <https://rk23.github.io/vesuvius-core-viewer/>. In the repository's
**Settings → Pages**, the publishing source is **GitHub Actions**. No custom domain is required.

The `Check and publish Vesuvius Core Viewer` workflow runs the checks above and exports `dist/site`.
Only successful runs on `main` upload that folder and deploy it to the `github-pages` environment.
Pull requests and other branches run the checks without publishing. The workflow also supports a
manual run from the Actions tab. All application and data paths are relative, so the viewer works
under the repository's `/vesuvius-core-viewer/` URL prefix.

Before a public release, inspect `git ls-files` and the staged diff, verify the license distinction
between software and data, and review the exported site. Public repository creation and hosting are
separate operations from preparing this local project.
