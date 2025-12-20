import time
from typing import Dict, List, Tuple

from civd.roi import roi_from_center_radius, roi_tiles
from civd.time_loader import load_index, decode_tile_from_entry


def build_lookup(idx: Dict):
    lut = {}
    for t in idx["tiles"]:
        c = t["tile_coords"]
        lut[(c["tz"], c["ty"], c["tx"])] = t
    return lut


def roi_tiles_at_time(index_path: str, center_zyx: Tuple[int, int, int], radius_vox: int):
    idx = load_index(index_path)
    Z, Y, X, _ = idx["volume"]["shape_zyxc"]
    roi = roi_from_center_radius(center_zyx, radius_vox, (Z, Y, X))
    tiles = roi_tiles(idx, roi)
    return idx, roi, tiles


def decode_roi(idx: Dict, tiles: List[Dict]):
    pack_path = idx["pack"]["path"]
    t0 = time.perf_counter()
    for e in tiles:
        _ = decode_tile_from_entry(e, pack_path)
    t1 = time.perf_counter()
    return (t1 - t0)


def main():
    t0_path = "data/civd_time/t000/index.json"
    t1_path = "data/civd_time/t001/index.json"

    # Choose ROI centered near the change center used in make_volume_t1.py
    center = (128, 128, 160)
    radius = 40

    idx0, roi0, tiles0 = roi_tiles_at_time(t0_path, center, radius)
    idx1, roi1, tiles1 = roi_tiles_at_time(t1_path, center, radius)

    # Identify which ROI tiles are actually changed in t001
    changed_in_t1 = [t for t in tiles1 if "ref" not in t]
    unchanged_in_t1 = [t for t in tiles1 if "ref" in t]

    dt0 = decode_roi(idx0, tiles0)
    dt1 = decode_roi(idx1, tiles1)

    print("CIVD Phase D — ROI @ Time + Delta Awareness")
    print("-----------------------------------------")
    print(f"ROI: {roi0}")
    print("")
    print("t000")
    print(f"  ROI tiles: {len(tiles0)}")
    print(f"  decode time: {dt0*1000:.2f} ms")
    print("")
    print("t001")
    print(f"  ROI tiles: {len(tiles1)}")
    print(f"  changed tiles inside ROI: {len(changed_in_t1)}")
    print(f"  unchanged tiles inside ROI (refs): {len(unchanged_in_t1)}")
    print(f"  decode time: {dt1*1000:.2f} ms")
    print("")
    print("Delta insight:")
    print(f"  Only {len(changed_in_t1)} tiles in the ROI required new storage for t001 (others reuse t000).")


if __name__ == "__main__":
    main()
