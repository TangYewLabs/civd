import time
from typing import Dict, List, Tuple

from civd.roi import roi_from_center_radius, roi_tiles
from civd.roi_delta import roi_delta_tiles
from civd.time_loader import load_index, decode_tile_from_entry


def decode_cost(idx: Dict, tiles: List[Dict]) -> Tuple[float, int, int]:
    """
    Returns:
      decode_time_s,
      compressed_bytes_read,
      tiles_decoded
    """
    pack_path = idx["pack"]["path"]
    comp_read = 0
    decoded = 0

    t0 = time.perf_counter()
    for t in tiles:
        if "ref" in t:
            comp_read += t["ref"]["length"]
        else:
            comp_read += t["length"]
        _ = decode_tile_from_entry(t, pack_path)
        decoded += 1
    t1 = time.perf_counter()

    return (t1 - t0), comp_read, decoded


def main():
    t0_path = "data/civd_time/t000/index.json"
    t1_path = "data/civd_time/t001/index.json"

    idx0 = load_index(t0_path)
    idx1 = load_index(t1_path)

    Z, Y, X, _ = idx0["volume"]["shape_zyxc"]

    # Same center used in your Phase D benchmark (near the changed region)
    center = (128, 128, 160)
    radius = 40

    roi = roi_from_center_radius(center, radius_vox=radius, vol_shape_zyx=(Z, Y, X))

    tiles_t0 = roi_tiles(idx0, roi)
    tiles_t1_full = roi_tiles(idx1, roi)
    tiles_t1_delta = roi_delta_tiles(idx1, roi)

    dt0, bytes0, n0 = decode_cost(idx0, tiles_t0)
    dt1, bytes1, n1 = decode_cost(idx1, tiles_t1_full)
    dtd, bytesd, nd = decode_cost(idx1, tiles_t1_delta)

    print("CIVD Phase D+ — ROI Delta-Only Decode Benchmark")
    print("------------------------------------------------")
    print(f"ROI: {roi}")
    print("")
    print("t000 (full ROI)")
    print(f"  tiles decoded: {n0}")
    print(f"  compressed bytes read: {bytes0:,}")
    print(f"  decode time: {dt0*1000:.2f} ms")
    print("")
    print("t001 (full ROI)")
    print(f"  tiles decoded: {n1}")
    print(f"  compressed bytes read: {bytes1:,}")
    print(f"  decode time: {dt1*1000:.2f} ms")
    print("")
    print("t001 (DELTA-only ROI)")
    print(f"  tiles decoded: {nd}")
    print(f"  compressed bytes read: {bytesd:,}")
    print(f"  decode time: {dtd*1000:.2f} ms")
    print("")
    if n1:
        print(f"Tile decode reduction: {n1} → {nd}  ({(1 - (nd / n1))*100:.2f}% fewer tiles)")
    if bytes1:
        print(f"Compressed IO reduction: {bytes1:,} → {bytesd:,}  ({(1 - (bytesd / bytes1))*100:.2f}% less IO)")


if __name__ == "__main__":
    main()
