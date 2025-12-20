import json
import os
import matplotlib.pyplot as plt


def main():
    path = "results/logs/usd_like_stream.json"
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)

    os.makedirs("results/plots", exist_ok=True)

    labels = ["t000 full", "t001 full", "t001 delta"]
    bytes_read = [
        d["t000_full"]["bytes_read"],
        d["t001_full"]["bytes_read"],
        d["t001_delta"]["bytes_read"],
    ]
    decode_ms = [
        d["t000_full"]["decode_ms"],
        d["t001_full"]["decode_ms"],
        d["t001_delta"]["decode_ms"],
    ]
    hits = [
        d["t000_full"]["hits"],
        d["t001_full"]["hits"],
        d["t001_delta"]["hits"],
    ]
    misses = [
        d["t000_full"]["misses"],
        d["t001_full"]["misses"],
        d["t001_delta"]["misses"],
    ]

    plt.figure()
    plt.title("CIVD G2 — USD-like Stream: Compressed Bytes Read")
    plt.bar(labels, bytes_read)
    plt.ylabel("Bytes (compressed)")
    plt.tight_layout()
    plt.savefig("results/plots/usd_like_bytes_read.png", dpi=160)
    plt.show()

    plt.figure()
    plt.title("CIVD G2 — USD-like Stream: Decode Time (ms)")
    plt.bar(labels, decode_ms)
    plt.ylabel("ms")
    plt.tight_layout()
    plt.savefig("results/plots/usd_like_decode_ms.png", dpi=160)
    plt.show()

    plt.figure()
    plt.title("CIVD G2 — USD-like Stream: Cache Hits vs Misses")
    x = range(len(labels))
    plt.bar(labels, hits, label="hits")
    plt.bar(labels, misses, bottom=hits, label="misses")
    plt.ylabel("Tiles")
    plt.legend()
    plt.tight_layout()
    plt.savefig("results/plots/usd_like_hits_misses.png", dpi=160)
    plt.show()

    print("Saved plots to results/plots/ (usd_like_*.png)")


if __name__ == "__main__":
    main()
