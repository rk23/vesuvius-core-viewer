# Credits and licenses

## CT imagery and derived visualization data

The bundled scenes derive from **Vesuvius Challenge — CT Scans of Herculaneum Papyri**, by Giorgio
Angelotti and collaborators. Credit the dataset using the current citation provided by the
[official data page](https://scrollprize.org/data#how-to-cite). All seven volume identifiers are
recorded in [data/catalog.json](data/catalog.json), including the 2025 PHerc. 1667 scan.

Source: [Vesuvius Challenge open data](https://scrollprize.org/data).
License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), reproduced verbatim in
[licenses/CT-DATA.txt](licenses/CT-DATA.txt) from the
[upstream notice](https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/LICENSE.txt).

Changes for this visualization: crops around an approximate center track, lower pyramid levels,
JPEG resizing/compression, intensity threshold selection and a bounded sample of voxel positions.
Some scenes include outlines extracted from nonzero CT cross-sections. Data has been repackaged as
compressed JSON with public volume provenance. The supplied CT-derived center tracks retain
CC BY-NC 4.0. No endorsement by the data providers is implied.

## Manual center axes

The axes for PHerc. 191, 257, 800, and 1218 are by **Alexey Drobkov**, from
[herculaneum-umbilici](https://github.com/AlexeyDrobkovStrikesBack/herculaneum-umbilici/tree/de7642ac9b38266e95192489e22fb13b7e2d13b6),
revision `de7642ac9b38266e95192489e22fb13b7e2d13b6`, under MIT.
The copyright and full notice are in [licenses/HERCULANEUM-UMBILICI.txt](licenses/HERCULANEUM-UMBILICI.txt).

The coordinate lists are preserved; files contain only the `control_points` needed by this viewer.
The scene axes are linear interpolations of those points. Each catalog entry links to its original
annotation file. The other three center tracks are approximate CT reference guides distributed with
their scene's data terms.

## Browser rendering

**Three.js 0.160.0 (r160)** and its OrbitControls are by the Three.js authors, under MIT.
[Upstream release](https://github.com/mrdoob/three.js/tree/r160),
[full notice](licenses/THREE.txt). Source URLs and SHA-256 checksums for vendored files and license
notices are recorded in [vendor/manifest.json](vendor/manifest.json).

## Viewer

The standalone viewer, scene preparation utilities, documentation, and tests are MIT licensed;
see [LICENSE](LICENSE). This project is independently maintained.
