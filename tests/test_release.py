import base64
import importlib.util
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from umbilicus_viewer.builder import Axis
from umbilicus_viewer.schema import read_scene

ROOT = Path(__file__).resolve().parents[1]


def test_distribution_boundary_and_checksums():
    spec = importlib.util.spec_from_file_location("verify_release", ROOT / "scripts/verify_release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.verify()["scenes"] == 7


def test_bundled_axes_match_scenes_and_images_have_no_annotations_metadata():
    catalog = json.loads((ROOT / "data/catalog.json").read_text())
    for entry in catalog["scenes"]:
        scene = read_scene(ROOT / entry["scene"])
        axis = Axis.from_json(ROOT / entry["axis"])
        sampled = np.array(scene["axis"])
        expected_x, expected_y = axis.at(sampled[:, 0])
        np.testing.assert_allclose(sampled[:, 1], expected_x, rtol=0, atol=1e-8)
        np.testing.assert_allclose(sampled[:, 2], expected_y, rtol=0, atol=1e-8)
        for s in scene["slices"]:
            with Image.open(io.BytesIO(base64.b64decode(s["jpg"]))) as image:
                assert image.mode == "L"
                assert not image.getexif()
                assert "comment" not in image.info and "xmp" not in image.info
