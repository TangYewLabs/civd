import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import zstandard as zstd


@dataclass(frozen=True)
class TileSpec:
    tile_z: int = 32
    tile_y: int = 32
    tile_x: int = 32
    channels: int = 2  # density + semantic-as-float32


def _iter_tile_bounds(vol_shape_zyxc: Tuple[int, int, int, int], spec: TileSpec):
    Z, Y, X, C = vol_shape_zyxc
    assert C == spec.channels, f"Expected C={spec.channels}, got C={C}"

    if (Z % spec.tile_z) or (Y % spec.tile_y) or (X % spec.tile_x):
        raise ValueError(
            f"Volume shape {vol_shape_zyxc} must be divisible by tile size "
            f"({spec.tile_z},{spec.tile_y},{spec.tile_x})."
        )

    nz = Z // spec.tile_z
    ny = Y // spec.tile_y
    nx = X // spec.tile_x

    for tz in range(nz):
        z0 = tz * spec.tile_z
        z1 = z0 + spec.tile_z
        for ty in range(ny):
            y0 = ty * spec.tile_y
            y1 = y0 + spec.tile_y
            for tx in range(nx):
                x0 = tx * spec.tile_x
                x1 = x0 + spec.tile_x
                tile_id = f"z{tz:02d}_y{ty:02d}_x{tx:02d}"
                yield tile_id, (z0, z1, y0, y1, x0, x1), (tz, ty, tx), (nz, ny, nx)


def build_tiles(
    volume_path: str = "data/volume.npy",
    out_dir: str = "data/civd_tiles",
    spec: TileSpec = TileSpec(),
    codec_level: int = 3,
) -> Dict:
    """
    Writes:
      - tiles.zstpack  (concatenated compressed tiles)
      - index.json     (tile metadata + byte offsets for random access)

    Returns:
      index dict (also written to index.json)
    """
    os.makedirs(out_dir, exist_ok=True)

    vol = np.load(volume_path)  # [Z,Y,X,C] float32
    if vol.dtype != np.float32:
        vol = vol.astype(np.float32, copy=False)

    Z, Y, X, C = vol.shape
    if C != spec.channels:
        raise ValueError(f"Expected {spec.channels} channels, got {C}")

    # Zstd compressor
    cctx = zstd.ZstdCompressor(level=codec_level)

    pack_path = os.path.join(out_dir, "tiles.zstpack")
    index_path = os.path.join(out_dir, "index.json")

    tile_entries: List[Dict] = []
    byte_offset = 0

    with open(pack_path, "wb") as fpack:
        for tile_id, bounds, tcoords, grid in _iter_tile_bounds(vol.shape, spec):
            z0, z1, y0, y1, x0, x1 = bounds
            tile = vol[z0:z1, y0:y1, x0:x1, :]  # float32 tile
            # Ensure contiguous bytes for consistent compression
            tile = np.ascontiguousarray(tile)

            raw = tile.tobytes(order="C")
            comp = cctx.compress(raw)

            fpack.write(comp)

            entry = {
                "tile_id": tile_id,
                "tile_coords": {"tz": tcoords[0], "ty": tcoords[1], "tx": tcoords[2]},
                "bounds": {"z0": z0, "z1": z1, "y0": y0, "y1": y1, "x0": x0, "x1": x1},
                "shape_zyxc": [spec.tile_z, spec.tile_y, spec.tile_x, spec.channels],
                "dtype": "float32",
                "codec": {"name": "zstd", "level": codec_level},
                "offset": byte_offset,
                "length": len(comp),
                "raw_nbytes": len(raw),
            }
            tile_entries.append(entry)
            byte_offset += len(comp)

    index = {
        "schema": "civd.phase_c.tilepack.v1",
        "volume": {"path": volume_path, "shape_zyxc": [Z, Y, X, C], "dtype": "float32"},
        "tile_spec": {"tile_z": spec.tile_z, "tile_y": spec.tile_y, "tile_x": spec.tile_x, "channels": spec.channels},
        "grid": {"nz": Z // spec.tile_z, "ny": Y // spec.tile_y, "nx": X // spec.tile_x, "tile_count": len(tile_entries)},
        "pack": {"path": pack_path, "format": "concat_zstd_frames"},
        "tiles": tile_entries,
    }

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    return index


if __name__ == "__main__":
    idx = build_tiles()
    print("Tile pack written:")
    print("  data/civd_tiles/tiles.zstpack")
    print("  data/civd_tiles/index.json")
    print(f"Tiles: {idx['grid']['tile_count']}  Grid: {idx['grid']['nz']}x{idx['grid']['ny']}x{idx['grid']['nx']}")
