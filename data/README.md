# Prepared center-view data

These are portable visualization scenes, derived from the public volumes linked in
[catalog.json](catalog.json). Scene files are gzip-compressed JSON; axes are plain coordinate JSON.
All CT imagery and derived CT visualization data retain CC BY-NC 4.0. The four Drobkov axes retain MIT.
See [../ATTRIBUTION.md](../ATTRIBUTION.md) and the individual catalog entries for credits and source links.

| Scroll | CT volume | L0 voxel µm | z range, L0 | Displayed CT points | CT slices | Scene MB |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| PHerc0175A | `20250521115057-8.640um-1.2m-116keV-masked.zarr` | 8.640 | 1700–11800 | 600,000 | 315 | 7.87 |
| PHerc0175B | `20250521125822-8.640um-1.2m-116keV-masked.zarr` | 8.640 | 1632–12960 | 600,000 | 177 | 7.21 |
| PHerc0191 | `20250821151635-9.362um-1.2m-113keV-masked.zarr` | 9.362 | 2000–18800 | 600,000 | 262 | 7.98 |
| PHerc0257 | `20250821151750-9.362um-1.2m-113keV-masked.zarr` | 9.362 | 1984–18240 | 510,790 | 254 | 6.09 |
| PHerc0800 | `20250521135224-8.640um-1.2m-116keV-masked.zarr` | 8.640 | 1728–23008 | 436,036 | 333 | 8.24 |
| PHerc1218 | `20250521120456-8.640um-1.2m-116keV-masked.zarr` | 8.640 | 1232–22064 | 600,000 | 325 | 9.50 |
| PHerc1667 | `20251217075048-2.399um-0.2m-78keV-masked.zarr` | 2.399 | 1536–36864 | 38,094 | 138 | 2.34 |

Sizes use decimal MB. Each volume is a masked uint8 Zarr scan. The point display selects CT intensity
at least 200 at pyramid level 2, except PHerc. 1667 at level 4; points are sampled to at most 600,000.
The existing displays used a minimum connected-component size of 8 per read slab. Cropped CT images
are reduced to approximately twice that level's voxel spacing and JPEG-compressed. These settings
control visualization and do not identify a physical material. Heights in `z_range` use an exclusive
upper bound.

Axis files retain the exact original coordinate control points. PHerc. 191, 257, 800, and 1218 use
Alexey Drobkov's manual axes at the pinned revision linked in the catalog. PHerc. 175A uses an
approximate center track; its reference range is z 4700–9100, with extrapolated sections also displayed.
PHerc. 175B uses an approximate automatic track, trimmed to z 1632–12960. PHerc. 1667 uses a rough
cross-section centroid track. All interpolation holds the endpoints beyond the input track.
The `axis_ok` field is a supplied reference range, not an independently measured accuracy guarantee.

Outlines are available for PHerc. 175A, 175B, and 1667. They show nonzero CT cross-sections of the
whole scroll, so they can extend beyond the radius of the central CT crop. Other scenes omit them.

`manifest.json` records SHA-256 checksums of all bundled scene and axis files and the catalog.
`data/local/` is ignored and reserved for your own scene files. The viewer can open custom files
without adding them to the catalog.
