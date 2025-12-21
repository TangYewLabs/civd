from __future__ import annotations

import os, json
import numpy as np
import zstandard as zstd
from typing import Dict

def load_index(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_comp_slice(pack_path: str, offset: int, length: int) -> bytes:
    with open(pack_path, "rb") as f:
        f.seek(offset)
        return f.read(length)

def _pack_path_from_index(idx: Dict[str, Any]) -> str:
    """
    Schema-tolerant resolver for the tile-pack path.

    Supports older and newer index layouts:
      - idx["pack"]["path"]
      - idx["pack_path"]
      - idx["tiles"]["pack_path"]
      - idx["tiles"]["pack"]["path"]
    """
    # Preferred: civd.index.v1 style
    pack = idx.get("pack")
    if isinstance(pack, dict):
        p = pack.get("path")
        if isinstance(p, str) and p:
            return p

    # Alternate flat forms
    p = idx.get("pack_path")
    if isinstance(p, str) and p:
        return p

    # Tiles section variants
    tiles = idx.get("tiles")
    if isinstance(tiles, dict):
        p = tiles.get("pack_path")
        if isinstance(p, str) and p:
            return p
        tpack = tiles.get("pack")
        if isinstance(tpack, dict):
            p = tpack.get("path")
            if isinstance(p, str) and p:
                return p

    raise KeyError("Could not resolve pack path from index (expected idx.pack.path or equivalent)")

def decode_tile_from_entry(entry: Dict, idx: Dict) -> tuple[np.ndarray, dict]:
    """
    Decode a tile entry for the current time index.

    Supports:
      - Direct tile payload: {offset,length,codec?} in the current pack
      - Ref to base pack slice (Phase D reuse): ref={base_pack,offset,length,codec?}
      - Ref to other time by (time,id): ref={time|base_timestamp, id|tile_id}
    """
    # --- helpers ---
    def _shape_and_tile_size(_idx: Dict) -> tuple[int, int]:
        shape_zyxc = _idx["volume"]["shape_zyxc"]
        C = int(shape_zyxc[3])
        tile_size = int(_idx["grid"]["tile_size"])
        return C, tile_size

    # --- current pack path ---
    pack_path = _pack_path_from_index(idx)

    # --- normalize ---
    ref = entry.get("ref", None)

    # If entry has direct bytes in current pack, use them
    if "offset" in entry and "length" in entry:
        offset = int(entry["offset"])
        length = int(entry["length"])
        C, tile_size = _shape_and_tile_size(idx)

        comp = _read_comp_slice(pack_path, offset, length)
        raw = zstd.ZstdDecompressor().decompress(comp)
        arr = np.frombuffer(raw, dtype=np.float32).reshape((tile_size, tile_size, tile_size, C))
        stats = {"bytes_read": length, "decoded_bytes": int(arr.nbytes), "ref_mode": "direct"}
        return arr, stats

    # If no ref, we cannot decode
    if ref is None:
        raise KeyError("tile entry missing offset/length and has no ref")

    # --- ref is a base-pack slice pointer (your current schema) ---
    if isinstance(ref, dict):
        base_pack = (
            ref.get("base_pack")
            or ref.get("pack")
            or ref.get("pack_path")
            or ref.get("path")
        )
        base_off = ref.get("offset")
        base_len = ref.get("length")

        if base_pack is not None and base_off is not None and base_len is not None:
            pack2 = str(base_pack).replace("\\", "/")
            offset2 = int(base_off)
            length2 = int(base_len)

            C, tile_size = _shape_and_tile_size(idx)

            comp = _read_comp_slice(pack2, offset2, length2)
            raw = zstd.ZstdDecompressor().decompress(comp)
            arr = np.frombuffer(raw, dtype=np.float32).reshape((tile_size, tile_size, tile_size, C))
            stats = {"bytes_read": length2, "decoded_bytes": int(arr.nbytes), "ref_mode": "pack_slice"}
            return arr, stats

        # --- fallback: ref points to another time by (time,id) ---
        ref_time = (
            ref.get("time")
            or ref.get("t")
            or ref.get("time_name")
            or ref.get("ref_time")
            or ref.get("base_time")
            or ref.get("base_timestamp")
        )
        ref_id = (
            ref.get("id")
            or ref.get("tile_id")
            or ref.get("tile")
            or ref.get("tid")
        )

        if not ref_time or not ref_id:
            raise KeyError(f"Unresolvable ref: {ref!r}")

        # Load base index and decode from that time's pack using id lookup
        base_index_path = os.path.join("data", "civd_time", str(ref_time), "index.json")
        base_idx = load_index(base_index_path)
        base_pack_path = _pack_path_from_index(base_idx)

        # build lookup dict for base tiles
        tiles = base_idx.get("tiles", [])
        found = None
        if isinstance(tiles, dict):
            found = tiles.get(ref_id)
        elif isinstance(tiles, list):
            for e in tiles:
                if isinstance(e, dict) and (e.get("id") == ref_id or e.get("tile_id") == ref_id):
                    found = e
                    break

        if found is None:
            raise KeyError(f"ref id not found in base index: time={ref_time} id={ref_id}")

        if "offset" not in found or "length" not in found:
            raise KeyError("base tile entry missing offset/length")

        offset3 = int(found["offset"])
        length3 = int(found["length"])
        C, tile_size = _shape_and_tile_size(base_idx)

        comp = _read_comp_slice(base_pack_path, offset3, length3)
        raw = zstd.ZstdDecompressor().decompress(comp)
        arr = np.frombuffer(raw, dtype=np.float32).reshape((tile_size, tile_size, tile_size, C))
        stats = {"bytes_read": length3, "decoded_bytes": int(arr.nbytes), "ref_mode": "time_id"}
        return arr, stats

    # --- ref as string/tuple/etc not supported in this build ---
    raise KeyError(f"Unresolvable ref type: {type(ref).__name__} value={ref!r}")

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
