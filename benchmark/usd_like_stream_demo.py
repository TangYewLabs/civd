import json
import os

from civd.roi import roi_from_center_radius
from civd.usd_stream import USDLikeStream


def main():
    os.makedirs("results/logs", exist_ok=True)

    center = (128, 128, 160)
    radius = 40

    # Stream t000 then t001, demonstrating cache reuse + delta load
    s0 = USDLikeStream("data/civd_time/t000/index.json", cache_tiles=128)
    Z, Y, X, _ = s0.idx["volume"]["shape_zyxc"]
    roi = roi_from_center_radius(center, radius, (Z, Y, X))

    _, st_full0 = s0.load_region(roi)

    s1 = USDLikeStream("data/civd_time/t001/index.json", cache_tiles=128)
    s1.cache._d = s0.cache._d  # carry cache forward like a long-lived session

    _, st_full1 = s1.load_region(roi)
    _, st_delta1 = s1.apply_delta(roi)

    log = {
        "roi": {"center": center, "radius": radius},
        "t000_full": st_full0.__dict__,
        "t001_full": st_full1.__dict__,
        "t001_delta": st_delta1.__dict__,
        "cache_tiles_after": len(s1.cache),
    }

    path = "results/logs/usd_like_stream.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    print("CIVD Phase G2 — USD-like Streaming Demo")
    print("--------------------------------------")
    print("ROI center:", center, "radius:", radius)
    print("")
    print("t000 load_region (full)")
    print("  hits/misses:", st_full0.hits, "/", st_full0.misses)
    print("  bytes_read:", st_full0.bytes_read)
    print("  decode_ms:", f"{st_full0.decode_ms:.2f}")
    print("")
    print("t001 load_region (full, with carried cache)")
    print("  hits/misses:", st_full1.hits, "/", st_full1.misses)
    print("  bytes_read:", st_full1.bytes_read)
    print("  decode_ms:", f"{st_full1.decode_ms:.2f}")
    print("")
    print("t001 apply_delta (changed-only tiles)")
    print("  hits/misses:", st_delta1.hits, "/", st_delta1.misses)
    print("  bytes_read:", st_delta1.bytes_read)
    print("  decode_ms:", f"{st_delta1.decode_ms:.2f}")
    print("")
    print("Saved:", path)


if __name__ == "__main__":
    main()
