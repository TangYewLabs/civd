import json
import os
import hashlib
from typing import Dict, Tuple, List

import numpy as np
import zstandard as zstd

from civd.tiler import TileSpec, _iter_tile_bounds


def tile_hash(tile: np.ndarray) -> str:
    """
    Stable hash of tile bytes (float32 contiguous).
    """
    tile = np.ascontiguousarray(tile.astype(np.float32, copy=False))
    h = hashlib.sha256(tile.tobytes(order="C")).hexdigest()
    return h


def build_timepack(
    volume_path: str,
    out_dir: str,
    spec: TileSpec = TileSpec(),
    codec_level: int = 3,
    timestamp: str = "t000",
    base_index_path: str = None,
) -> Dict:
    """
    If base_index_path is provided, writes ONLY changed tiles relative to base index.
    Unchanged tiles are referenced via 'ref' entries pointing to base pack + offsets.

    Writes:
      out_dir/tiles.zstpack
      out_dir/index.json
    """
    os.makedirs(out_dir, exist_ok=True)

    vol = np.load(volume_path)
    if vol.dtype != np.float32:
        vol = vol.astype(np.float32, copy=False)

    Z, Y, X, C = vol.shape

    base = None
    if base_index_path:
        with open(base_index_path, "r", encoding="utf-8") as f:
            base = json.load(f)

    cctx = zstd.ZstdCompressor(level=codec_level)
    pack_path = os.path.join(out_dir, "tiles.zstpack")
    index_path = os.path.join(out_dir, "index.json")

    tile_entries: List[Dict] = []
    byte_offset = 0

    # Build base tile hash lookup if base exists
    base_hash = {}
    base_lookup = {}
    if base:
        for t in base["tiles"]:
            base_hash[t["tile_id"]] = t.get("hash")
            base_lookup[t["tile_id"]] = t

    changed = 0
    unchanged = 0

    with open(pack_path, "wb") as fpack:
        for tile_id, bounds, tcoords, grid in _iter_tile_bounds(vol.shape, spec):
            z0, z1, y0, y1, x0, x1 = bounds
            tile = np.ascontiguousarray(vol[z0:z1, y0:y1, x0:x1, :])

            h = tile_hash(tile)

            if base and base_hash.get(tile_id) == h:
                # Unchanged: reference base tile entry
                bt = base_lookup[tile_id]
                tile_entries.append({
                    "tile_id": tile_id,
                    "tile_coords": bt["tile_coords"],
                    "bounds": bt["bounds"],
                    "shape_zyxc": bt["shape_zyxc"],
                    "dtype": bt["dtype"],
                    "hash": h,
                    "ref": {
                        "base_timestamp": base.get("timestamp", "t000"),
                        "base_index": base_index_path,
                        "base_pack": base["pack"]["path"],
                        "offset": bt["offset"],
                        "length": bt["length"],
                        "codec": bt["codec"],
                    }
                })
                unchanged += 1
                continue

            # Changed (or no base): write as new compressed tile in this timepack
            raw = tile.tobytes(order="C")
            comp = cctx.compress(raw)
            fpack.write(comp)

            tile_entries.append({
                "tile_id": tile_id,
                "tile_coords": {"tz": tcoords[0], "ty": tcoords[1], "tx": tcoords[2]},
                "bounds": {"z0": z0, "z1": z1, "y0": y0, "y1": y1, "x0": x0, "x1": x1},
                "shape_zyxc": [spec.tile_z, spec.tile_y, spec.tile_x, spec.channels],
                "dtype": "float32",
                "hash": h,
                "codec": {"name": "zstd", "level": codec_level},
                "offset": byte_offset,
                "length": len(comp),
                "raw_nbytes": len(raw),
            })
            byte_offset += len(comp)
            changed += 1

    index = {
        "schema": "civd.phase_d.timepack.v1",
        "timestamp": timestamp,
        "volume": {"path": volume_path, "shape_zyxc": [Z, Y, X, C], "dtype": "float32"},
        "tile_spec": {"tile_z": spec.tile_z, "tile_y": spec.tile_y, "tile_x": spec.tile_x, "channels": spec.channels},
        "grid": {"nz": Z // spec.tile_z, "ny": Y // spec.tile_y, "nx": X // spec.tile_x, "tile_count": len(tile_entries)},
        "pack": {"path": pack_path, "format": "concat_zstd_frames"},
        "base_index": base_index_path,
        "stats": {"changed_tiles": changed, "unchanged_tiles": unchanged},
        "tiles": tile_entries,
    }

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    return index


if __name__ == "__main__":
    # Build t000 from the original volume
    idx0 = build_timepack(
        volume_path="data/volume.npy",
        out_dir="data/civd_time/t000",
        timestamp="t000",
        base_index_path=None
    )
    print("Built t000:", idx0["stats"])

    # Build t001 storing only changed tiles relative to t000
    idx1 = build_timepack(
        volume_path="data/volume_t1.npy",
        out_dir="data/civd_time/t001",
        timestamp="t001",
        base_index_path="data/civd_time/t000/index.json"
    )
    print("Built t001:", idx1["stats"])
    print("Wrote:")
    print("  data/civd_time/t000/index.json")
    print("  data/civd_time/t001/index.json")
