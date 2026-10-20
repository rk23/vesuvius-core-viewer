import base64
import json
import subprocess
import sys

import numpy as np
import pytest
import zarr

from umbilicus_viewer.builder import Axis, build_scene, clustered, feature_mask, open_volume
from umbilicus_viewer.schema import read_scene, validate_scene, write_scene


def straight_axis(x=32, y=32):
    return Axis(np.array([0, 100]), np.array([x, x]), np.array([y, y]))


def settings(**overrides):
    return {"title": "Synthetic CT", "voxel_um": 1, "level": 1, "z_range": (0, 16),
            "radius_mm": 0.01, "slice_every": 4, **overrides}


def unpack(scene):
    packed = np.frombuffer(base64.b64decode(scene["points_b64"]), dtype="<i2").reshape(-1, 3)
    return packed * scene["step_vx"] + scene["origin"]


def test_axis_formats_interpolation_and_endpoints(tmp_path):
    for data in [
        {"control_points": [{"x": 10, "y": 20, "z": 100}, {"x": 30, "y": 40, "z": 200}]},
        {"track_points": {"200": [30, 40], "100": [10, 20]}},
    ]:
        path = tmp_path / "axis.json"
        path.write_text(json.dumps(data))
        axis = Axis.from_json(path)
        assert axis.at(150) == (20, 30)
        assert axis.at(-100) == (10, 20)
        assert axis.at(500) == (30, 40)


@pytest.mark.parametrize("points", [[], [{"x": 1, "y": 2, "z": 3}] * 2,
                                   [{"x": 1, "y": 2, "z": 3}, {"x": 4, "y": 5, "z": float("nan")}]])
def test_bad_axes_fail_before_sampling(tmp_path, points):
    path = tmp_path / "axis.json"
    path.write_text(json.dumps({"control_points": points}))
    with pytest.raises(ValueError):
        Axis.from_json(path)


def test_ct_xyz_frame_and_pyramid_scale():
    ct = np.zeros((8, 32, 32), dtype=np.uint8)
    ct[2, 16, 18] = 240
    ct[3, 19, 16] = 230
    ct[4, 1, 1] = 250  # outside the displayed cylinder
    scene = build_scene(ct, straight_axis(), **settings())
    assert scene["points_total"] == 2
    assert {tuple(p) for p in unpack(scene)} == {(36, 32, 4), (32, 38, 6)}
    assert [s["z"] for s in scene["slices"]] == [0, 4, 8, 12]
    assert all((s["cx"], s["cy"]) == (32, 32) for s in scene["slices"])


def test_edge_crop_and_empty_cloud_are_valid():
    scene = build_scene(np.full((8, 16, 16), 100, dtype=np.uint8), straight_axis(0, 0), **settings())
    assert scene["points_total"] == 0
    assert scene["points_b64"] == ""
    assert len(scene["slices"]) == 4
    assert scene["slices"][0]["cx"] == 0


def test_cloud_cap_is_deterministic_and_preserves_total():
    ct = np.full((8, 32, 32), 250, dtype=np.uint8)
    a = build_scene(ct, straight_axis(), **settings(max_points=25))
    b = build_scene(ct, straight_axis(), **settings(max_points=25))
    assert a["points_total"] > 25
    assert len(unpack(a)) == 25
    assert a["points_b64"] == b["points_b64"]
    assert len(np.unique(unpack(a), axis=0)) == 25


def test_dark_feature_and_optional_component_filter():
    assert feature_mask(np.array([0, 10, 100, 250]), "dark", 100).tolist() == [False, True, True, False]
    mask = np.zeros((5, 10, 10), dtype=bool)
    mask[2, 2, 2] = True
    mask[1:4, 5:8, 5:8] = True
    result = clustered(mask, 8)
    assert result.sum() == 27 and not result[2, 2, 2]


def test_outline_uses_full_cross_section():
    ct = np.zeros((8, 32, 32), dtype=np.uint8)
    ct[:, 3:29, 3:29] = 100
    scene = build_scene(ct, straight_axis(), **settings(outline_every=8))
    assert [o["z"] for o in scene["envelope"]] == [0, 8]
    xy = np.array(scene["envelope"][0]["xy"]).reshape(-1, 2)
    assert xy[:, 0].min() < 12 and xy[:, 0].max() > 52


def test_scene_boundary_and_deterministic_compression(tmp_path):
    scene = build_scene(np.zeros((8, 32, 32), dtype=np.uint8), straight_axis(), **settings())
    one, two = tmp_path / "one.json.gz", tmp_path / "two.json.gz"
    write_scene(scene, one)
    write_scene(scene, two)
    assert one.read_bytes() == two.read_bytes()
    assert read_scene(one) == scene
    with pytest.raises(ValueError, match="expected exactly"):
        validate_scene({**scene, "attachment": "arbitrary bytes"})
    scene["provenance"]["volume_url"] = "https://example.org/ct?token=example"
    with pytest.raises(ValueError, match="public HTTP"):
        validate_scene(scene)


def test_local_zarr_cli_round_trip_without_local_paths(tmp_path):
    group = zarr.open_group(str(tmp_path / "ct.zarr"), mode="w")
    ct = group.create_dataset("1", shape=(8, 32, 32), chunks=(4, 16, 16), dtype="uint8")
    ct[2, 16, 18] = 250
    axis = tmp_path / "axis.json"
    axis.write_text(json.dumps({"track_points": {"0": [32, 32], "16": [32, 32]}}))
    output = tmp_path / "scene.json.gz"
    result = subprocess.run([
        sys.executable, "-m", "umbilicus_viewer", "build", "--volume", str(tmp_path / "ct.zarr"),
        "--axis", str(axis), "--voxel-um", "1", "--level", "1", "--z", "0", "16",
        "--radius-mm", "0.01", "--slice-every", "4", "--output", str(output),
    ], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    scene = read_scene(output)
    assert tuple(unpack(scene)[0]) == (36, 32, 4)
    assert str(tmp_path) not in json.dumps(scene)
    assert scene["provenance"]["data_license"] == "unspecified"
    assert open_volume(str(tmp_path / "ct.zarr" / "1"), 1).shape == (8, 32, 32)


def test_invalid_volume_range_is_rejected():
    with pytest.raises(ValueError, match="extent"):
        build_scene(np.zeros((8, 32, 32), dtype=np.uint8), straight_axis(),
                    **settings(z_range=(0, 100)))
