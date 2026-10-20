"""Prepare CT voxel locations, image crops and an axis for the browser viewer."""

from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from .schema import validate_scene


@dataclass
class Axis:
    z: np.ndarray
    x: np.ndarray
    y: np.ndarray

    @classmethod
    def from_json(cls, path: str | Path) -> Axis:
        data = json.loads(Path(path).read_text())
        if "control_points" in data:
            points = [(p["z"], p["x"], p["y"]) for p in data["control_points"]]
        elif "track_points" in data:
            points = [(float(z), p[0], p[1]) for z, p in data["track_points"].items()]
        else:
            raise ValueError("Axis JSON needs control_points or track_points")
        a = np.asarray(sorted(points), dtype=np.float64)
        if a.ndim != 2 or a.shape[1] != 3 or len(a) < 2 or not np.isfinite(a).all():
            raise ValueError("Axis needs at least two finite xyz control points")
        if np.any(np.diff(a[:, 0]) <= 0):
            raise ValueError("Axis control points must have unique heights")
        return cls(a[:, 0], a[:, 1], a[:, 2])

    def at(self, z):
        """Linearly interpolate xy at height z; hold endpoint values beyond the ends."""
        return np.interp(z, self.z, self.x), np.interp(z, self.z, self.y)


def feature_mask(image, feature: str, threshold: float):
    return image >= threshold if feature == "bright" else (image > 0) & (image <= threshold)


def clustered(mask, minimum: int):
    if minimum <= 1 or not mask.any():
        return mask
    labels, _ = ndimage.label(mask)
    keep = np.bincount(labels.ravel()) >= minimum
    keep[0] = False
    return keep[labels]


def open_volume(source: str, level: int):
    """Open a read-only Zarr v2 array or a 2**level multiscale group in zyx order."""
    import fsspec
    import zarr

    options = {"anon": True} if source.startswith("s3://") else {}
    store = fsspec.get_mapper(source, **options)
    root = zarr.open(store, mode="r")
    array = root if hasattr(root, "shape") else root[str(level)]
    if len(array.shape) != 3 or array.dtype != np.dtype("uint8"):
        raise ValueError("Expected a 3D uint8 Zarr array in z,y,x order")
    return array


def build_scene(
    volume, axis: Axis, *, title: str, voxel_um: float, level: int, z_range: tuple[int, int],
    radius_mm: float = 10, threshold: float = 200, feature: str = "bright", max_points: int = 600_000,
    slice_every: int = 64, min_cluster: int = 1, outline_every: int = 0, axis_ok=None,
    source_url: str = "", data_license: str = "unspecified", data_attribution: str = "User-provided CT data",
) -> dict:
    if level < 0 or voxel_um <= 0 or radius_mm <= 0 or max_points < 1 or slice_every < 1:
        raise ValueError("Level must be nonnegative; dimensions and sample counts must be positive")
    if not np.isfinite([voxel_um, radius_mm, threshold]).all() or not 0 < threshold <= 255:
        raise ValueError("Dimensions must be finite and the threshold must be in (0, 255]")
    if feature not in {"bright", "dark"} or min_cluster < 1 or outline_every < 0:
        raise ValueError("Invalid feature or display sampling settings")
    if len(volume.shape) != 3 or volume.dtype != np.dtype("uint8"):
        raise ValueError("Expected uint8 CT in z,y,x order")
    factor = 2 ** level
    z0, z1 = z_range
    if not 0 <= z0 < z1 <= volume.shape[0] * factor:
        raise ValueError("z_range must lie inside the volume's level-0 extent")
    start, end = -(-z0 // factor), -(-z1 // factor)
    if start >= end:
        raise ValueError("z_range contains no samples at the requested pyramid level")
    radius = radius_mm * 1000 / voxel_um
    half = max(1, int(np.ceil(radius / factor)))
    rng = np.random.default_rng(0)
    clouds, priorities, pending, total = [], [], 0, 0
    slices, outlines = [], []
    last_slice, last_outline = -np.inf, -np.inf

    def reduce_cloud():
        nonlocal clouds, priorities, pending
        points = np.concatenate(clouds) if clouds else np.empty((0, 3), dtype=np.float64)
        keys = np.concatenate(priorities) if priorities else np.empty(0)
        if len(points) > max_points:
            indices = np.argpartition(keys, max_points - 1)[:max_points]
            points, keys = points[indices], keys[indices]
        clouds, priorities, pending = [points], [keys], len(points)
        return points

    for first in range(start, end, 32):
        stop = min(first + 32, end)
        zs = np.arange(first, stop) * factor
        ax, ay = axis.at(zs)
        xs, ys = np.rint(ax / factor).astype(int), np.rint(ay / factor).astype(int)
        x0, x1 = max(0, int(xs.min()) - half), min(volume.shape[2], int(xs.max()) + half + 1)
        y0, y1 = max(0, int(ys.min()) - half), min(volume.shape[1], int(ys.max()) + half + 1)
        if x0 >= x1 or y0 >= y1:
            raise ValueError("The supplied axis lies outside the CT volume")
        slab = np.asarray(volume[first:stop, y0:y1, x0:x1])
        # Connected-component filtering is optional and local to each read slab.
        mask = clustered(feature_mask(slab, feature, threshold), min_cluster)
        for k, (z, cx, cy) in enumerate(zip(zs, xs, ys)):
            yy, xx = np.nonzero(mask[k])
            gx, gy = (xx + x0) * factor, (yy + y0) * factor
            select = np.hypot(gx - ax[k], gy - ay[k]) <= radius
            points = np.column_stack([gx[select], gy[select], np.full(select.sum(), z)])
            total += len(points)
            if len(points):
                clouds.append(points)
                priorities.append(rng.random(len(points)))
                pending += len(points)
                if pending > 2 * max_points:
                    reduce_cloud()
            if z - last_slice >= slice_every:
                image = np.zeros((2 * half + 1, 2 * half + 1), dtype=np.uint8)
                ix0, ix1 = max(cx - half, x0), min(cx + half + 1, x1)
                iy0, iy1 = max(cy - half, y0), min(cy + half + 1, y1)
                image[iy0 - cy + half:iy1 - cy + half, ix0 - cx + half:ix1 - cx + half] = (
                    slab[k, iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0]
                )
                thumb = Image.fromarray(image).resize((half + 1, half + 1), Image.Resampling.BILINEAR)
                buffer = io.BytesIO()
                thumb.save(buffer, "JPEG", quality=82)
                slices.append({"z": int(z), "cx": int(cx * factor), "cy": int(cy * factor),
                               "half_vx": (half + 0.5) * factor,
                               "jpg": base64.b64encode(buffer.getvalue()).decode()})
                last_slice = z
            if outline_every and z - last_outline >= outline_every:
                from skimage.measure import find_contours

                mask2d = ndimage.binary_fill_holes(np.asarray(volume[int(z // factor)]) > 0)
                labels, count = ndimage.label(mask2d)
                if count:
                    largest = labels == np.bincount(labels.ravel())[1:].argmax() + 1
                    contours = find_contours(np.pad(largest, 1).astype(float), 0.5)
                    contour = max(contours, key=len) - 1
                    contour = contour[::max(1, len(contour) // 256), ::-1] * factor
                    outlines.append({"z": int(z), "xy": contour.round(2).ravel().tolist()})
                last_outline = z
        print(f"z {int(zs[-1])}: {total} feature voxels; {len(slices)} CT slices", flush=True)
    points = reduce_cloud()
    origin = points.min(0) if len(points) else np.array([0, 0, z0])
    packed = np.rint((points - origin) / factor)
    if packed.size and (packed.max() > 32767 or packed.min() < -32768):
        raise ValueError("Point coordinates exceed int16 range; use a coarser level or a shorter z range")
    az = np.unique(np.r_[z0, np.arange(z0, z1, 100), z1])
    ax, ay = axis.at(az)
    mx, my = axis.at((z0 + z1) / 2)
    scene = {
        "schema_version": 1, "title": title, "voxel_mm": voxel_um / 1000, "step_vx": factor,
        "origin": origin.tolist(), "centre": [float(mx), float(my), (z0 + z1) / 2],
        "z_range": [int(z0), int(z1)], "radius_mm": radius_mm,
        "axis": np.column_stack([az, ax, ay]).tolist(), "axis_ok": list(axis_ok) if axis_ok else None,
        "points_b64": base64.b64encode(packed.astype("<i2").tobytes()).decode(), "points_total": total,
        "feature_text": f"CT {'≥' if feature == 'bright' else '≤'} {threshold:g} at {voxel_um * factor:.1f} µm",
        "slices": slices, "envelope": outlines, "slice_um": voxel_um * factor * (2 * half + 1) / (half + 1),
        "provenance": {
            "volume_url": source_url, "data_license": data_license, "data_attribution": data_attribution,
            "data_reference": "", "axis_source": "User-supplied coordinate points.",
            "axis_license": "unspecified", "axis_note": "User-supplied axis; verify its coordinate frame.",
            "display": "Cropped, downsampled CT slices and threshold-selected CT voxel locations.",
        },
    }
    return validate_scene(scene)
