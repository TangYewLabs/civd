import json
from typing import Dict, List, Tuple

import numpy as np
import zstandard as zstd


def load_index(path: str = "data/civd_tiles/index.json") -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_tile(pack_path: str, tile_entry: Dict) -> np.ndarray:
    """
    Random-access read + decompress a single tile from the pack.
    Returns float32 array shaped [tile_z, tile_y, tile_x, C]
    """
    offset = tile_entry["offset"]
    length = tile_entry["length"]
    shape = tuple(tile_entry["shape_zyxc"])

    with open(pack_path, "rb") as f:
        f.seek(offset)
        comp = f.read(length)

    dctx = zstd.ZstdDecompressor()
    raw = dctx.decompress(comp)

    arr = np.frombuffer(raw, dtype=np.float32).reshape(shape)
    return arr


def read_tiles(pack_path: str, tile_entries: List[Dict]) -> List[np.ndarray]:
    """
    Read multiple tiles. Keeps implementation simple and correct.
    (We will optimize IO later only if needed.)
    """
    out = []
    for t in tile_entries:
        out.append(read_tile(pack_path, t))
    return out


if __name__ == "__main__":
    idx = load_index()
    pack = idx["pack"]["path"]
    t0 = idx["tiles"][0]
    a = read_tile(pack, t0)
    print("Read tile:", t0["tile_id"], "shape:", a.shape, "min/max:", float(a.min()), float(a.max()))
