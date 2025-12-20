import json
import os
import time
from typing import Optional

import numpy as np

from bridge.msg import SubmapDeltaMsg


def publish_to_dir(msg: SubmapDeltaMsg, out_dir: str = "bridge_out") -> str:
    """
    Writes a 'topic message' to disk:
      - <name>.npz : tiles + bounds + roi
      - <name>.json: metadata
    Returns the base path (without extension).
    """
    os.makedirs(out_dir, exist_ok=True)

    ts = msg.timestamp
    name = f"civd_submap_{ts}_{msg.mode}_{int(time.time()*1000)}"
    base = os.path.join(out_dir, name)

    np.savez_compressed(
        base + ".npz",
        tiles=msg.tiles,
        tile_bounds_zyx=msg.tile_bounds_zyx,
        roi=np.array(msg.roi_zyx, dtype=np.int32),
        timestamp=ts,
        mode=msg.mode,
    )

    meta = {
        "schema": msg.schema,
        "timestamp": msg.timestamp,
        "mode": msg.mode,
        "roi_zyx": list(msg.roi_zyx),
        "tile_count": int(msg.tiles.shape[0]),
        "compressed_bytes_read_est": msg.compressed_bytes_read_est,
        "decode_ms": msg.decode_ms,
        "npz_path": base + ".npz",
    }

    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return base


def load_from_base(base_path: str) -> SubmapDeltaMsg:
    """
    Loads a message written by publish_to_dir().
    """
    meta_path = base_path + ".json"
    npz_path = base_path + ".npz"

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    d = np.load(npz_path, allow_pickle=True)

    msg = SubmapDeltaMsg(
        schema=meta["schema"],
        timestamp=str(d["timestamp"]),
        mode=str(d["mode"]),
        roi_zyx=tuple(d["roi"].tolist()),
        tile_bounds_zyx=d["tile_bounds_zyx"],
        tiles=d["tiles"],
        compressed_bytes_read_est=meta.get("compressed_bytes_read_est"),
        decode_ms=meta.get("decode_ms"),
    )
    return msg
