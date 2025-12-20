import json
import numpy as np
import zstandard as zstd

INDEX = "data/civd_tiles/index.json"

with open(INDEX, "r", encoding="utf-8") as f:
    idx = json.load(f)

pack_path = idx["pack"]["path"]
tile0 = idx["tiles"][0]

z0 = tile0["offset"]
z1 = z0 + tile0["length"]
shape = tuple(tile0["shape_zyxc"])
dtype = np.float32

with open(pack_path, "rb") as f:
    f.seek(z0)
    comp = f.read(tile0["length"])

dctx = zstd.ZstdDecompressor()
raw = dctx.decompress(comp)
arr = np.frombuffer(raw, dtype=dtype).reshape(shape)

print("Read tile:", tile0["tile_id"])
print("Tile shape:", arr.shape, "dtype:", arr.dtype)
print("min/max:", float(arr.min()), float(arr.max()))
