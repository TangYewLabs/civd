import json
import matplotlib.pyplot as plt

t0 = "data/civd_time/t000/index.json"
t1 = "data/civd_time/t001/index.json"

with open(t0, "r", encoding="utf-8") as f:
    idx0 = json.load(f)
with open(t1, "r", encoding="utf-8") as f:
    idx1 = json.load(f)

c0 = idx0["stats"]["changed_tiles"]
u0 = idx0["stats"]["unchanged_tiles"]
c1 = idx1["stats"]["changed_tiles"]
u1 = idx1["stats"]["unchanged_tiles"]

plt.figure()
plt.title("CIVD Phase D — Changed-Tile-Only Temporal Update")
plt.bar(["t000 changed", "t000 unchanged", "t001 changed", "t001 unchanged"], [c0, u0, c1, u1])
plt.ylabel("Tile count")
plt.tight_layout()
plt.savefig("results/plots/timepack_changed_vs_reused.png", dpi=160)
plt.show()

print("Saved: results/plots/timepack_changed_vs_reused.png")
print(f"t000: changed={c0}, reused={u0}")
print(f"t001: changed={c1}, reused={u1}")
