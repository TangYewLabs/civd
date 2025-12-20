import json
import time
import tracemalloc
from dataclasses import asdict
from typing import Dict, List, Set, Tuple

from civd.roi import roi_from_center_radius, roi_tiles
from civd.loader import load_index, read_tile


def tile_key(entry: Dict) -> Tuple[int, int, int]:
    c = entry["tile_coords"]
    return (c["tz"], c["ty"], c["tx"])


def stream_benchmark(index: Dict, steps: int = 20, radius_vox: int = 40, stride_vox: int = 16):
    """
    Simulates a moving ROI across the volume and measures:
      - tiles requested per step
      - cache hits vs misses
      - compressed bytes read (misses only)
      - decode time (misses only)
    """
    vol_shape = index["volume"]["shape_zyxc"]
    Z, Y, X, _ = vol_shape
    pack_path = index["pack"]["path"]

    # Prebuild a lookup from tile coords -> tile entry
    lookup = {}
    for t in index["tiles"]:
        lookup[tile_key(t)] = t

    cache: Set[Tuple[int, int, int]] = set()

    # Start near one side, move across X
    cz, cy = Z // 2, Y // 2
    start_x = 48
    results = []

    total_comp_read = 0
    total_decode_s = 0.0
    total_misses = 0
    total_hits = 0
    total_tiles_requested = 0

    for i in range(steps):
        cx = min(X - 1, start_x + i * stride_vox)
        roi = roi_from_center_radius((cz, cy, cx), radius_vox=radius_vox, vol_shape_zyx=(Z, Y, X))
        tiles = roi_tiles(index, roi)

        requested = [tile_key(t) for t in tiles]
        requested_set = set(requested)

        hits = sum(1 for k in requested if k in cache)
        misses = len(requested) - hits

        # Decode only misses (simulate streaming/cache behavior)
        t0 = time.perf_counter()
        comp_read = 0
        for k in requested:
            if k in cache:
                continue
            entry = lookup[k]
            comp_read += entry["length"]
            _ = read_tile(pack_path, entry)  # decode (we discard array; we measure cost)
            cache.add(k)
        t1 = time.perf_counter()

        dt = (t1 - t0) if misses > 0 else 0.0

        total_tiles_requested += len(requested)
        total_hits += hits
        total_misses += misses
        total_comp_read += comp_read
        total_decode_s += dt

        results.append({
            "step": i,
            "center_zyx": (cz, cy, cx),
            "tiles_requested": len(requested),
            "hits": hits,
            "misses": misses,
            "compressed_bytes_read": comp_read,
            "decode_time_s": dt,
            "cache_size_tiles": len(cache),
        })

    summary = {
        "steps": steps,
        "radius_vox": radius_vox,
        "stride_vox": stride_vox,
        "total_tiles_requested": total_tiles_requested,
        "total_hits": total_hits,
        "total_misses": total_misses,
        "hit_rate": (total_hits / total_tiles_requested) if total_tiles_requested else 0.0,
        "total_compressed_bytes_read": total_comp_read,
        "total_decode_time_s": total_decode_s,
        "avg_decode_time_per_step_s": (total_decode_s / steps) if steps else 0.0,
    }

    return results, summary


def main():
    idx = load_index()

    tracemalloc.start()
    snap0 = tracemalloc.take_snapshot()

    results, summary = stream_benchmark(idx, steps=20, radius_vox=40, stride_vox=16)

    snap1 = tracemalloc.take_snapshot()
    mem_stats = snap1.compare_to(snap0, "lineno")
    mem_delta = sum(s.size_diff for s in mem_stats)

    print("CIVD Phase C — Dynamic ROI Streaming Benchmark")
    print("---------------------------------------------")
    print(f"Steps: {summary['steps']}  radius_vox: {summary['radius_vox']}  stride_vox: {summary['stride_vox']}")
    print("")
    print(f"Total tiles requested: {summary['total_tiles_requested']}")
    print(f"Total hits:            {summary['total_hits']}")
    print(f"Total misses:          {summary['total_misses']}")
    print(f"Hit rate:              {summary['hit_rate']*100:.2f}%")
    print("")
    print(f"Total compressed read: {summary['total_compressed_bytes_read']:,} bytes")
    print(f"Total decode time:     {summary['total_decode_time_s']*1000:.2f} ms")
    print(f"Avg decode/step:       {summary['avg_decode_time_per_step_s']*1000:.2f} ms")
    print("")
    print(f"Approx mem delta (tracemalloc): {mem_delta/1e6:.2f} MB")
    print("")
    print("First 5 steps (tiles/hits/misses/MB read/ms):")
    for r in results[:5]:
        mb = r["compressed_bytes_read"] / 1e6
        ms = r["decode_time_s"] * 1000
        print(f"  step {r['step']:02d}: tiles={r['tiles_requested']:3d} hits={r['hits']:3d} misses={r['misses']:3d} read={mb:6.2f}MB  dt={ms:6.2f}ms")

    out = {
        "summary": summary,
        "steps": results,
        "mem_delta_bytes": int(mem_delta),
    }
    with open("results/logs/stream_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("Saved: results/logs/stream_benchmark.json")


if __name__ == "__main__":
    main()
