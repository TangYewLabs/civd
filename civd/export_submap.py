import json
import os
import time
from dataclasses import asdict
from typing import Dict, List, Tuple

import numpy as np

from civd.roi import roi_from_center_radius, roi_tiles, ROIBox
from civd.roi_delta import roi_delta_tiles
from civd.time_loader import load_index, decode_tile_from_entry


def _tile_bounds_to_tuple(tb: Dict) -> Tuple[int, int, int, int, int, int]:
    return tb["z0"], tb["z1"], tb["y0"], tb["y1"], tb["x0"], tb["x1"]


def export_submap(
    index_path: str,
    center_zyx: Tuple[int, int, int],
    radius_vox: int,
    mode: str = "full",  # "full" or "delta"
    out_dir: str = "exports",
) -> Dict:
    """
    Exports a submap payload from a CIVD timepack index:
      - mode="full": exports all tiles in ROI at this timestamp
      - mode="delta": exports only changed tiles in ROI (tiles without 'ref')

    Outputs:
      exports/submap_<timestamp>_<mode>_<z>_<y>_<x>_r<r>.npz
      exports/submap_<timestamp>_<mode>_<z>_<y>_<x>_r<r>.json
    """
    idx = load_index(index_path)
    pack_path = idx["pack"]["path"]

    Z, Y, X, C = idx["volume"]["shape_zyxc"]
    roi = roi_from_center_radius(center_zyx, radius_vox, (Z, Y, X))

    if mode not in ("full", "delta"):
        raise ValueError("mode must be 'full' or 'delta'")

    tiles = roi_tiles(idx, roi) if mode == "full" else roi_delta_tiles(idx, roi)

    os.makedirs(out_dir, exist_ok=True)

    # Decode tiles
    t0 = time.perf_counter()
    decoded = []
    bounds = []
    tile_ids = []
    coords = []
    comp_bytes = 0

    for t in tiles:
        tile_ids.append(t["tile_id"])
        c = t["tile_coords"]
        coords.append((c["tz"], c["ty"], c["tx"]))

        b = t["bounds"]
        bounds.append(_tile_bounds_to_tuple(b))

        # estimate bytes read (compressed)
        if "ref" in t:
            comp_bytes += int(t["ref"]["length"])
        else:
            comp_bytes += int(t["length"])

        arr = decode_tile_from_entry(t, pack_path)
        decoded.append(arr)

    t1 = time.perf_counter()

    if decoded:
        tiles_arr = np.stack(decoded, axis=0).astype(np.float32, copy=False)
    else:
        # Empty delta case is valid: no changed tiles in ROI
        tiles_arr = np.zeros((0, 1, 1, 1, C), dtype=np.float32)

    bounds_arr = np.array(bounds, dtype=np.int32) if bounds else np.zeros((0, 6), dtype=np.int32)
    coords_arr = np.array(coords, dtype=np.int16) if coords else np.zeros((0, 3), dtype=np.int16)
    tile_ids_arr = np.array(tile_ids, dtype=object)

    ts = idx.get("timestamp", "tXXX")
    cz, cy, cx = center_zyx
    fname = f"submap_{ts}_{mode}_z{cz}_y{cy}_x{cx}_r{radius_vox}"

    npz_path = os.path.join(out_dir, fname + ".npz")
    json_path = os.path.join(out_dir, fname + ".json")

    np.savez_compressed(
       npz_path,
       tiles=tiles_arr,
       tile_ids=tile_ids_arr,
       tile_coords=coords_arr,
       tile_bounds_zyx=bounds_arr,
       roi=np.array([roi.z0, roi.z1, roi.y0, roi.y1, roi.x0, roi.x1], dtype=np.int32),
       timestamp=ts,
       mode=mode,
    )


    meta = {
        "schema": "civd.phase_e.submap.v1",
        "timestamp": ts,
        "mode": mode,
        "index_path": index_path,
        "pack_path": pack_path,
        "volume_shape_zyxc": idx["volume"]["shape_zyxc"],
        "roi": asdict(roi) if hasattr(roi, "__dict__") else {
            "z0": roi.z0, "z1": roi.z1, "y0": roi.y0, "y1": roi.y1, "x0": roi.x0, "x1": roi.x1
        },
        "tile_count": int(len(tiles)),
        "compressed_bytes_read_est": int(comp_bytes),
        "decode_ms": float((t1 - t0) * 1000.0),
        "npz_path": npz_path,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return meta


if __name__ == "__main__":
    # Default demo export near the change center you used earlier
    base = "data/civd_time/t000/index.json"
    upd = "data/civd_time/t001/index.json"
    center = (128, 128, 160)
    r = 40

    m0 = export_submap(base, center, r, mode="full")
    print("Exported:", m0["npz_path"])
    print("  tiles:", m0["tile_count"], "decode_ms:", f'{m0["decode_ms"]:.2f}', "bytes:", m0["compressed_bytes_read_est"])

    m1 = export_submap(upd, center, r, mode="full")
    print("Exported:", m1["npz_path"])
    print("  tiles:", m1["tile_count"], "decode_ms:", f'{m1["decode_ms"]:.2f}', "bytes:", m1["compressed_bytes_read_est"])

    md = export_submap(upd, center, r, mode="delta")
    print("Exported:", md["npz_path"])
    print("  tiles:", md["tile_count"], "decode_ms:", f'{md["decode_ms"]:.2f}', "bytes:", md["compressed_bytes_read_est"])
