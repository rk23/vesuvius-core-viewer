# Vesuvius Core Viewer

A browser tool for exploring the center of a CT-scanned papyrus scroll in 3D. Rotate around a reference
axis, scrub through CT slices, and view threshold-selected CT points by angle, height, or distance from
the center. Seven prepared scenes are included.

## Open the viewer

From this repository, run:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000>. Select a scroll in the sidebar. Everything needed to view the included
scenes is bundled locally, including Three.js; viewing them requires no external network requests,
Python packages, accounts, or CT downloads. Use a current browser with WebGL and `DecompressionStream`
support. Serve the files over HTTP so browser modules and scene loading work.

Drag to rotate, right-drag to pan, and scroll to zoom. The view buttons provide top, front, and side
views. The CT slider moves the cross-section; “Centre on slice” moves the camera target to it.
“Fit view” frames the central CT region in the current direction.
Radius and height controls filter the point cloud. The outer outline control appears when a scene
includes whole-scroll cross-sections.

## Included data

PHerc. 175A, 175B, 191, 257, 800, 1218, and 1667. The bundle contains cropped CT JPEGs, sampled CT
voxel coordinates, reference axes, and available outlines. See [data/README.md](data/README.md) for
volume identifiers, sampling, sizes, and axis attribution.

Coordinates use the original scan's level-0 voxels: x and y in the axial plane and z along the stack.
The viewer draws increasing z downward and uses millimeters for distances. Center tracks are
approximate reference guides; their stated reference ranges remain visible. CT thresholds are display
settings, and intensity alone does not identify a material.

## Prepare a scene from your own CT

This optional step requires Python 3.12+ and [uv](https://docs.astral.sh/uv/):

```sh
uv sync --extra build
uv run --extra build python -m umbilicus_viewer build \
  --volume /path/to/volume.zarr --axis /path/to/axis.json \
  --voxel-um 8.64 --level 2 --z 4000 6000 --radius-mm 8 \
  --title "Scroll center" --output data/local/scene.json.gz
```

Open the resulting file with “Open scene file” in the sidebar. File loading happens entirely in the
browser. Local scenes are ignored by Git. An HTTP-served scene can also be opened with
`?file=data/local/scene.json.gz`; included scenes have links such as `?scene=PHerc0191`.

The builder accepts read-only Zarr v2 arrays or groups with pyramid levels `0`, `1`, …, in z,y,x
order with uint8 intensities. A chosen level must have scale `2**level`; voxel size must be isotropic.
Anonymous `s3://` sources are supported. Use a small height range first to bound downloads and memory.
Axis files accept either `control_points: [{"x":…, "y":…, "z":…}, …]` or
`track_points: {"z": [x, y], …}`. Points are interpolated linearly and held at the endpoints.

`--slice-every` and `--outline-every` use level-0 voxel distances; outlines are disabled by default.
`--max-points` bounds the displayed sample using a fixed random seed. `--feature dark` excludes zero
background. Optional `--min-cluster` filtering applies within each read slab. Use `--source-url`,
`--data-license`, and `--data-attribution` to supply public provenance. Local filesystem paths are
never embedded in generated scenes. New scenes start with an unspecified license.

## Development and release

```sh
uv sync --extra build --group dev
uv run pytest
uv run ruff check .
python3 scripts/verify_release.py
python3 scripts/export_site.py dist/site
```

The last command creates a static-site folder containing only the viewer, prepared data, credits,
and required license notices. See [docs/RELEASE.md](docs/RELEASE.md) for browser checks and release scope.

## Licenses and credits

Viewer code: [MIT](LICENSE). Bundled CT imagery and derived visualization data: **CC BY-NC 4.0**,
which retains the upstream noncommercial restriction. Four manually annotated axes: MIT, copyright
Alexey Drobkov. Three.js: MIT, copyright its authors. These assets retain their own terms;
the code license does not relicense the data. Full notices and source links are in
[ATTRIBUTION.md](ATTRIBUTION.md) and [licenses/](licenses/).
