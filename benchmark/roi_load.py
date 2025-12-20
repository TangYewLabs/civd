import json
import time
import tracemalloc

import numpy as np

from civd.roi import roi_from_center_radius, roi_tiles
from civd.loader import load_index, read_tiles


def full_load(volume_path="data/volume.npy"):
    t0 = time.perf_counter()
    vol = np.load(volume_path)
    t1 = time.perf_counter()
    return vol, (t1 - t0)


def roi_load(index, radius_vox=40):
    vol_shape = index["volume"]["shape_zyxc"]
    Z, Y, X, _ = vol_shape
    roi = roi_from_center_radius((Z // 2, Y // 2, X // 2), radius_vox=radius_vox, vol_shape_zyx=(Z, Y, X))
    tiles = roi_tiles(index, roi)

    pack_path = index["pack"]["path"]

    t0 = time.perf_counter()
    decoded = read_tiles(pack_path, tiles)
    t1 = time.perf_counter()

    decoded_bytes = sum(t["raw_nbytes"] for t in tiles)
    compressed_bytes = sum(t["length"] for t in tiles)

    return {
        "roi": roi,
        "tile_count": len(tiles),
        "decode_time_s": (t1 - t0),
        "decoded_bytes": decoded_bytes,
        "compressed_bytes_read": compressed_bytes,
        "decoded_tiles": decoded,  # keep for potential follow-up validation
    }


def main():
    idx = load_index()

    # Track memory
    tracemalloc.start()

    # Full load benchmark
    snap0 = tracemalloc.take_snapshot()
    vol, t_full = full_load(idx["volume"]["path"])
    snap1 = tracemalloc.take_snapshot()

    full_stats = snap1.compare_to(snap0, "lineno")
    full_mem = sum(s.size_diff for s in full_stats)

    # ROI load benchmark
    snap2 = tracemalloc.take_snapshot()
    roi_res = roi_load(idx, radius_vox=40)
    snap3 = tracemalloc.take_snapshot()

    roi_stats = snap3.compare_to(snap2, "lineno")
    roi_mem = sum(s.size_diff for s in roi_stats)

    # Report
    total_volume_bytes = vol.nbytes

    print("CIVD Phase C — ROI Benchmark")
    print("---------------------------")
    print(f"Volume shape: {tuple(vol.shape)} dtype={vol.dtype} bytes={total_volume_bytes:,}")
    print("")
    print("FULL LOAD")
    print(f"  np.load time: {t_full*1000:.2f} ms")
    print(f"  approx mem delta (tracemalloc): {full_mem/1e6:.2f} MB")
    print("")
    print("ROI LOAD (tile-pack)")
    print(f"  ROI vox: {roi_res['roi']}")
    print(f"  tiles loaded: {roi_res['tile_count']}")
    print(f"  compressed bytes read: {roi_res['compressed_bytes_read']:,}")
    print(f"  decoded bytes produced: {roi_res['decoded_bytes']:,}")
    print(f"  decode time: {roi_res['decode_time_s']*1000:.2f} ms")
    print(f"  approx mem delta (tracemalloc): {roi_mem/1e6:.2f} MB")
    print("")
    pct = 100.0 * (roi_res["decoded_bytes"] / total_volume_bytes)
    print(f"ROI decoded as % of full volume: {pct:.2f}%")

    # Save a JSON record for repeatability
    out = {
        "volume_shape": list(vol.shape),
        "volume_bytes": int(total_volume_bytes),
        "full_load_time_s": float(t_full),
        "roi": {
            "z0": roi_res["roi"].z0, "z1": roi_res["roi"].z1,
            "y0": roi_res["roi"].y0, "y1": roi_res["roi"].y1,
            "x0": roi_res["roi"].x0, "x1": roi_res["roi"].x1,
        },
        "roi_tile_count": int(roi_res["tile_count"]),
        "roi_decode_time_s": float(roi_res["decode_time_s"]),
        "roi_compressed_bytes_read": int(roi_res["compressed_bytes_read"]),
        "roi_decoded_bytes": int(roi_res["decoded_bytes"]),
        "roi_fraction_of_volume": float(pct / 100.0),
    }

    with open("results/logs/roi_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("Saved: results/logs/roi_benchmark.json")


if __name__ == "__main__":
    main()
