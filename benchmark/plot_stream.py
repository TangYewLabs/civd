import json
import matplotlib.pyplot as plt

with open("results/logs/stream_benchmark.json", "r", encoding="utf-8") as f:
    data = json.load(f)

steps = data["steps"]
x = [s["step"] for s in steps]
misses = [s["misses"] for s in steps]
hits = [s["hits"] for s in steps]
read_mb = [s["compressed_bytes_read"] / 1e6 for s in steps]
dt_ms = [s["decode_time_s"] * 1000 for s in steps]

plt.figure()
plt.title("CIVD Phase C — Dynamic ROI Streaming (Cache Behavior)")
plt.plot(x, hits, label="Cache hits (tiles)")
plt.plot(x, misses, label="Cache misses (tiles)")
plt.xlabel("Step")
plt.ylabel("Tile count")
plt.legend()
plt.tight_layout()
plt.savefig("results/plots/stream_hits_misses.png", dpi=160)
plt.show()

plt.figure()
plt.title("CIVD Phase C — Streaming Cost Per Step")
plt.plot(x, read_mb, label="Compressed MB read")
plt.xlabel("Step")
plt.ylabel("MB")
plt.legend()
plt.tight_layout()
plt.savefig("results/plots/stream_mb_read.png", dpi=160)
plt.show()

plt.figure()
plt.title("CIVD Phase C — Decode Time Per Step (Misses Only)")
plt.plot(x, dt_ms, label="Decode time (ms)")
plt.xlabel("Step")
plt.ylabel("ms")
plt.legend()
plt.tight_layout()
plt.savefig("results/plots/stream_decode_ms.png", dpi=160)
plt.show()

print("Saved plots to results/plots/")
