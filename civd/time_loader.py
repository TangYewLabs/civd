import json
from typing import Dict, List, Optional

import numpy as np
import zstandard as zstd


def load_index(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_comp_slice(pack_path: str, offset: int, length: int) -> bytes:
    with open(pack_path, "rb") as f:
        f.seek(offset)
        return f.read(length)


def decode_tile_from_entry(entry: Dict, default_pack_path: str) -> np.ndarray:
    """
    Decodes a tile entry. If entry contains 'ref', it reads from the base pack.
    Otherwise reads from the current pack.
    """
    # Determine pack + offsets
    if "ref" in entry:
        ref = entry["ref"]
        pack_path = ref["base_pack"]
        offset = ref["offset"]
        length = ref["length"]
    else:
        pack_path = default_pack_path
        offset = entry["offset"]
        length = entry["length"]

    comp = _read_comp_slice(pack_path, offset, length)
    dctx = zstd.ZstdDecompressor()
    raw = dctx.decompress(comp)

    shape = tuple(entry["shape_zyxc"])
    arr = np.frombuffer(raw, dtype=np.float32).reshape(shape)
    return arr


def decode_tiles(index_path: str, tile_entries: List[Dict]) -> List[np.ndarray]:
    """
    Decode a list of tile entries given an index.json path.
    """
    idx = load_index(index_path)
    pack_path = idx["pack"]["path"]

    out = []
    for e in tile_entries:
        out.append(decode_tile_from_entry(e, pack_path))
    return out


if __name__ == "__main__":
    idx1 = load_index("data/civd_time/t001/index.json")
    pack1 = idx1["pack"]["path"]

    # Pick one unchanged tile and one changed tile
    unchanged = next(t for t in idx1["tiles"] if "ref" in t)
    changed = next(t for t in idx1["tiles"] if "ref" not in t)

    a = decode_tile_from_entry(unchanged, pack1)
    b = decode_tile_from_entry(changed, pack1)

    print("Unchanged tile:", unchanged["tile_id"], "ref->", unchanged["ref"]["base_timestamp"], "min/max:", float(a.min()), float(a.max()))
    print("Changed tile:  ", changed["tile_id"], "local", "min/max:", float(b.min()), float(b.max()))
