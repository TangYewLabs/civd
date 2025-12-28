from __future__ import annotations

import os
from typing import Optional, Tuple

import numpy as np

from civd.source import VolumePacket


def _write_ply_xyzrgb(path: str, xyz: np.ndarray, rgb: Optional[np.ndarray] = None) -> None:
    """
    Write an ASCII PLY with x,y,z and optional r,g,b (uint8).
    """
    n = int(xyz.shape[0])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    has_rgb = rgb is not None
    with open(path, "w", encoding="utf-8") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {n}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        if has_rgb:
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
        f.write("end_header\n")

        if has_rgb:
            for (x, y, z), (r, g, b) in zip(xyz, rgb):
                f.write(f"{x:.6f} {y:.6f} {z:.6f} {int(r)} {int(g)} {int(b)}\n")
        else:
            for (x, y, z) in xyz:
                f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")


def volume_to_pointcloud_ply(
    pkt: VolumePacket,
    out_path: str,
    *,
    occupancy_channel: int = 0,
    threshold: float = 0.5,
    stride: int = 1,
    color_mode: str = "none",
) -> Tuple[str, int]:
    """
    Convert a VolumePacket volume (Z,Y,X,C) to a point cloud PLY.

    - occupancy_channel: which channel represents occupancy/density
    - threshold: include voxels where volume[...,occupancy_channel] >= threshold
    - stride: subsample grid to reduce points (1 = no subsample)
    - color_mode:
        "none"      -> xyz only
        "by_value"  -> grayscale based on occupancy value
    Returns: (out_path, num_points)
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    vol = np.asarray(pkt.volume, dtype=np.float32)
    if vol.ndim != 4:
        raise ValueError("Expected pkt.volume shape (Z,Y,X,C)")

    Z, Y, X, C = vol.shape
    if occupancy_channel < 0 or occupancy_channel >= C:
        raise ValueError(f"occupancy_channel out of range (C={C})")

    occ = vol[..., occupancy_channel]

    if stride > 1:
        occ_s = occ[::stride, ::stride, ::stride]
        z_idx, y_idx, x_idx = np.where(occ_s >= threshold)
        # map back to full-res indices
        z_idx = z_idx * stride
        y_idx = y_idx * stride
        x_idx = x_idx * stride
    else:
        z_idx, y_idx, x_idx = np.where(occ >= threshold)

    n = int(z_idx.shape[0])
    if n == 0:
        # write empty ply
        _write_ply_xyzrgb(out_path, np.zeros((0, 3), dtype=np.float32), None)
        return out_path, 0

    # Convert to world coordinates by adding ROI origin.
    # Note: coordinates are voxel centers in index space.
    xyz = np.stack(
        [
            (x_idx + pkt.roi.x0).astype(np.float32),
            (y_idx + pkt.roi.y0).astype(np.float32),
            (z_idx + pkt.roi.z0).astype(np.float32),
        ],
        axis=1,
    )

    rgb = None
    if color_mode == "by_value":
        vals = occ[z_idx, y_idx, x_idx]
        vals = np.clip(vals, 0.0, 1.0)
        g = (vals * 255.0).astype(np.uint8)
        rgb = np.stack([g, g, g], axis=1)
    elif color_mode != "none":
        raise ValueError("color_mode must be 'none' or 'by_value'")

    _write_ply_xyzrgb(out_path, xyz, rgb)
    return out_path, n
