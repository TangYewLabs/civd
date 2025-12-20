from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List

from civd.schema import (
    SCHEMA_INDEX_V1,
    _as_int_list6,
    infer_tile_size_from_bounds,
    verify_index_v1,
)


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def infer_tile_size(idx: Dict[str, Any], default_ts: int = 32) -> int:
    # If already present anywhere, use it.
    grid = idx.get("grid")
    if isinstance(grid, dict) and "tile_size" in grid:
        return int(grid["tile_size"])

    tiles = idx.get("tiles")
    if isinstance(tiles, list) and len(tiles) > 0:
        e0 = tiles[0]
        if isinstance(e0, dict):
            b = e0.get("bounds_zyx") or e0.get("bounds") or e0.get("bounds_zyx6")
            if b is not None:
                b6 = _as_int_list6(b)
                return infer_tile_size_from_bounds(b6)

    return int(default_ts)


def upgrade_index_inplace(index_path: str, *, default_tile_size: int = 32) -> None:
    idx = load_json(index_path)

    # Ensure top-level schema_version
    idx["schema_version"] = SCHEMA_INDEX_V1

    # Ensure volume.shape_zyxc exists in object form
    if "volume" not in idx or not isinstance(idx["volume"], dict):
        # Try to lift legacy
        if "shape_zyxc" in idx:
            idx["volume"] = {"shape_zyxc": idx["shape_zyxc"]}
        else:
            raise RuntimeError("Cannot upgrade: missing volume.shape_zyxc (or legacy shape_zyxc)")

    # Ensure pack.path exists in object form
    if "pack" not in idx or not isinstance(idx["pack"], dict):
        if "pack_path" in idx:
            idx["pack"] = {"path": idx["pack_path"]}
        else:
            raise RuntimeError("Cannot upgrade: missing pack.path (or legacy pack_path)")

    # Tile size
    ts = infer_tile_size(idx, default_ts=default_tile_size)

    # Ensure grid object
    if "grid" not in idx or not isinstance(idx["grid"], dict):
        idx["grid"] = {}
    idx["grid"]["tile_size"] = int(ts)

    # Normalize each tile entry
    tiles = idx.get("tiles")
    if not isinstance(tiles, list) or len(tiles) == 0:
        raise RuntimeError("Cannot upgrade: tiles must be a non-empty list")

    for i, e in enumerate(tiles):
        if not isinstance(e, dict):
            raise RuntimeError(f"Tile entry {i} is not an object")
        # Normalize bounds_zyx to list-of-6 ints
        if "bounds_zyx" in e:
            e["bounds_zyx"] = _as_int_list6(e["bounds_zyx"])
        elif "bounds" in e:
            e["bounds_zyx"] = _as_int_list6(e["bounds"])
            del e["bounds"]
        elif "bounds_zyx6" in e:
            e["bounds_zyx"] = _as_int_list6(e["bounds_zyx6"])
            del e["bounds_zyx6"]
        else:
            # If missing entirely, we cannot standardize safely. Fail fast.
            raise RuntimeError(f"Tile entry {i} missing bounds; cannot upgrade to v1")

        # Optional: ensure tile_id exists
        if "tile_id" not in e:
            # Try legacy key names
            if "id" in e:
                e["tile_id"] = e["id"]
                del e["id"]
            elif "tile" in e:
                e["tile_id"] = e["tile"]
                del e["tile"]
            else:
                raise RuntimeError(f"Tile entry {i} missing tile_id")

    # Validate upgraded index
    verify_index_v1(idx)

    # Write back
    save_json(index_path, idx)


def main() -> None:
    ap = argparse.ArgumentParser(description="Upgrade CIVD index.json to civd.index.v1")
    ap.add_argument("--time", required=True, help="time pack, e.g., t000 or t001")
    ap.add_argument("--root", default=".", help="repo root (default: .)")
    ap.add_argument("--default-tile-size", type=int, default=32, help="fallback tile size if not inferable")
    args = ap.parse_args()

    index_path = os.path.join(args.root, "data", "civd_time", args.time, "index.json")
    if not os.path.exists(index_path):
        raise SystemExit(f"Index not found: {index_path}")

    upgrade_index_inplace(index_path, default_tile_size=args.default_tile_size)
    print(f"Upgraded index to {SCHEMA_INDEX_V1}: {index_path}")


if __name__ == "__main__":
    main()
