from __future__ import annotations

import argparse

from .schema import read_scene, write_scene


def main():
    parser = argparse.ArgumentParser(description="Prepare or validate scroll-center CT viewer scenes")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="Validate a portable JSON or JSON.gz scene")
    check.add_argument("scene")
    build = commands.add_parser("build", help="Read CT and axis points into a portable viewer scene")
    build.add_argument("--volume", required=True, help="Zarr v2 group or array; local path or anonymous S3 URL")
    build.add_argument("--axis", required=True, help="JSON control_points or track_points in level-0 xyz voxels")
    build.add_argument("--voxel-um", required=True, type=float, help="Isotropic level-0 voxel size in micrometers")
    build.add_argument("--z", required=True, type=int, nargs=2, metavar=("Z0", "Z1"))
    build.add_argument("--level", type=int, default=2, help="Pyramid level with scale 2**level (default 2)")
    build.add_argument("--radius-mm", type=float, default=10)
    build.add_argument("--threshold", type=float, default=200)
    build.add_argument("--feature", choices=["bright", "dark"], default="bright")
    build.add_argument("--max-points", type=int, default=600_000)
    build.add_argument("--slice-every", type=int, default=64, help="CT slice spacing in level-0 voxels")
    build.add_argument("--min-cluster", type=int, default=1, help="Optional minimum component size per read slab")
    build.add_argument("--outline-every", type=int, default=0, help="Full cross-section outline spacing; 0 disables")
    build.add_argument("--axis-ok", type=int, nargs=2, help="Reference range for the supplied axis")
    build.add_argument("--source-url", default="", help="Optional public CT source URL, without query strings")
    build.add_argument("--data-license", default="unspecified")
    build.add_argument("--data-attribution", default="User-provided CT data")
    build.add_argument("--title", default="Scroll center")
    build.add_argument("--output", required=True, help="Scene JSON or JSON.gz path")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            scene = read_scene(args.scene)
            print(f"Valid scene: {scene['title']} ({len(scene['slices'])} CT slices)")
            return
        from .builder import Axis, build_scene, open_volume

        settings = vars(args).copy()
        for name in ["command", "volume", "axis", "output", "z"]:
            settings.pop(name)
        if args.level < 0:
            raise ValueError("Level must be nonnegative")
        axis = Axis.from_json(args.axis)
        volume = open_volume(args.volume, args.level)
        scene = build_scene(volume, axis, z_range=tuple(args.z), **settings)
        write_scene(scene, args.output)
        print(args.output)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
