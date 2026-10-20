"""Strict, visualization-only scene format; no optional opaque attachments."""

from __future__ import annotations

import base64
import gzip
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

SCENE_FIELDS = {
    "schema_version", "title", "voxel_mm", "step_vx", "origin", "centre", "z_range", "radius_mm",
    "axis", "axis_ok", "points_b64", "points_total", "feature_text", "slices", "envelope", "slice_um",
    "provenance",
}
PROVENANCE_FIELDS = {
    "volume_url", "data_license", "data_attribution", "data_reference", "axis_source", "axis_license",
    "axis_note", "display",
}
SLICE_FIELDS = {"z", "cx", "cy", "half_vx", "jpg"}
MAX_SCENE_BYTES = 128 * 1024 * 1024


def _keys(value, expected, name):
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{name}: expected exactly {sorted(expected)}")


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Coordinates and dimensions must be finite numbers")
    return value


def _vector(value, length):
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"Expected a vector of length {length}")
    return [_number(v) for v in value]


def _public_url(value):
    if not value:
        return
    u = urlsplit(value)
    if u.scheme not in {"http", "https"} or not u.netloc or u.username or u.password or u.query:
        raise ValueError("Source links must be public HTTP(S) URLs without credentials or query strings")


def validate_scene(data: dict) -> dict:
    _keys(data, SCENE_FIELDS, "scene")
    if data["schema_version"] != 1 or isinstance(data["schema_version"], bool):
        raise ValueError("Unsupported scene schema version")
    for field in ["title", "feature_text", "points_b64"]:
        if not isinstance(data[field], str):
            raise ValueError(f"{field}: expected text")
    for field in ["voxel_mm", "step_vx", "radius_mm", "slice_um"]:
        if _number(data[field]) <= 0:
            raise ValueError(f"{field}: expected a positive number")
    for field in ["origin", "centre"]:
        _vector(data[field], 3)
    z0, z1 = _vector(data["z_range"], 2)
    if z1 <= z0:
        raise ValueError("z_range must increase")
    if data["axis_ok"] is not None:
        lo, hi = _vector(data["axis_ok"], 2)
        if hi < lo:
            raise ValueError("axis_ok must increase")
    if not isinstance(data["axis"], list) or len(data["axis"]) < 2:
        raise ValueError("An axis requires at least two points")
    axis = [_vector(p, 3) for p in data["axis"]]
    if any(a[0] >= b[0] for a, b in zip(axis, axis[1:])):
        raise ValueError("Axis heights must strictly increase")
    points = base64.b64decode(data["points_b64"], validate=True)
    if len(points) % 6:
        raise ValueError("Point data must contain little-endian int16 xyz triples")
    total = data["points_total"]
    if isinstance(total, bool) or not isinstance(total, int) or total < len(points) // 6:
        raise ValueError("points_total must include every displayed point")
    if not isinstance(data["slices"], list) or not isinstance(data["envelope"], list):
        raise ValueError("slices and envelope must be lists")
    previous = -math.inf
    for s in data["slices"]:
        _keys(s, SLICE_FIELDS, "slice")
        for field in ["z", "cx", "cy", "half_vx"]:
            _number(s[field])
        if s["half_vx"] <= 0 or not z0 <= s["z"] < z1 or s["z"] <= previous:
            raise ValueError("CT slices need positive size and increasing heights inside z_range")
        previous = s["z"]
        image = base64.b64decode(s["jpg"], validate=True)
        if not image.startswith(b"\xff\xd8") or not image.endswith(b"\xff\xd9"):
            raise ValueError("CT slices must be JPEG images")
    for loop in data["envelope"]:
        _keys(loop, {"z", "xy"}, "outline")
        if not z0 <= _number(loop["z"]) < z1:
            raise ValueError("Outline height is outside z_range")
        xy = loop["xy"]
        if not isinstance(xy, list) or len(xy) < 6 or len(xy) % 2:
            raise ValueError("Outline must have at least three xy pairs")
        for value in xy:
            _number(value)
    _keys(data["provenance"], PROVENANCE_FIELDS, "provenance")
    if any(not isinstance(v, str) for v in data["provenance"].values()):
        raise ValueError("Provenance values must be text")
    for field in ["volume_url", "data_reference"]:
        _public_url(data["provenance"][field])
    return data


def read_scene(path: str | Path) -> dict:
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        raw = stream.read(MAX_SCENE_BYTES + 1)
    if len(raw) > MAX_SCENE_BYTES:
        raise ValueError("Scene exceeds the 128 MiB uncompressed size limit")
    return validate_scene(json.loads(raw))


def write_scene(data: dict, path: str | Path) -> None:
    validate_scene(data)
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    if len(raw) > MAX_SCENE_BYTES:
        raise ValueError("Scene exceeds the 128 MiB uncompressed size limit")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz":
        with path.open("wb") as stream:
            with gzip.GzipFile(filename="", fileobj=stream, mode="wb", mtime=0) as compressed:
                compressed.write(raw)
    else:
        path.write_bytes(raw)
