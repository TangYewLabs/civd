from __future__ import annotations

import os
from typing import Any, Dict

import numpy as np

from civd.source import VolumePacket


def volume_to_voxelgrid_npz(pkt: VolumePacket, out_path: str) -> str:
    """
    Export a CIVD VolumePacket to a compact NPZ artifact usable by any toolchain.

    Contents:
      - volume: float32 array (roiZ, roiY, roiX, C)
      - roi: int64 array [z0,z1,y0,y1,x0,x1] (world-space bounds)
      - meta: python dict stored as object array (portable enough for demos)
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    roi = np.array(
        [pkt.roi.z0, pkt.roi.z1, pkt.roi.y0, pkt.roi.y1, pkt.roi.x0, pkt.roi.x1],
        dtype=np.int64,
    )

    meta: Dict[str, Any] = {
        "schema_version": pkt.schema_version,
        "time_name": pkt.time,
        "mode": pkt.mode,
        "shape_zyxc": pkt.shape_zyxc,
        "tile_size": int(pkt.tile_size),
        "tiles_total": int(pkt.tiles_total),
        "tiles_included": int(pkt.tiles_included),
        "bytes_read": int(pkt.bytes_read),
        "decode_ms": float(pkt.decode_ms),
        "channels": list(pkt.channels),
    }

    np.savez_compressed(
        out_path,
        volume=np.asarray(pkt.volume, dtype=np.float32),
        roi=roi,
        meta=np.array([meta], dtype=object),
    )
    return out_path
