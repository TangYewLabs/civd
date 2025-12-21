from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Tuple

import numpy as np

def _pack_path_from_index(idx: dict) -> str:
    """
    Schema-tolerant pack path resolver.

    Supports:
      - legacy: idx["pack"] == "data/.../tiles.zstpack"
      - v1:     idx["pack"] == {"path": "data/.../tiles.zstpack", ...}
    """
    pack = idx.get("pack")

    if isinstance(pack, str):
        return pack

    if isinstance(pack, dict):
        p = pack.get("path") or pack.get("pack_path")
        if not p:
            raise KeyError("index.pack.path missing")
        return str(p)

    raise TypeError(f"Unsupported index.pack type: {type(pack).__name__}")

from civd.roi import roi_from_center_radius
from civd.time_loader import load_index, decode_tile_from_entry

SCHEMA_SUBMAP_V1 = "civd.submap.v1"


def _tile_id_from_tcoords(tz: int, ty: int, tx: int) -> str:
    return f"z{tz:02d}_y{ty:02d}_x{tx:02d}"


def _roi_tcoord_ranges(roi, tile_size: int) -> Tuple[range, range, range]:
    tz0 = int(roi.z0) // tile_size
    tz1 = (int(roi.z1) - 1) // tile_size
    ty0 = int(roi.y0) // tile_size
    ty1 = (int(roi.y1) - 1) // tile_size
    tx0 = int(roi.x0) // tile_size
    tx1 = (int(roi.x1) - 1) // tile_size
    return range(tz0, tz1 + 1), range(ty0, ty1 + 1), range(tx0, tx1 + 1)


def _bounds6_from_entry(entry: Dict[str, Any], *, tile_size: int) -> List[int]:
    """
    Return [z0,z1,y0,y1,x0,x1] for a tile entry, tolerant to schema variants.
    Prefers explicit bounds_zyx, then bounds, else derives from tz/ty/tx.
    """
    b = entry.get("bounds_zyx", None)
    if b is None:
        b = entry.get("bounds", None)

    if isinstance(b, (list, tuple)) and len(b) == 6:
        return [int(x) for x in b]

    if isinstance(b, dict):
        if all(k in b for k in ("z0", "z1", "y0", "y1", "x0", "x1")):
            return [int(b["z0"]), int(b["z1"]), int(b["y0"]), int(b["y1"]), int(b["x0"]), int(b["x1"])]
        if all(k in b for k in ("z", "y", "x")):
            z, y, x = b["z"], b["y"], b["x"]
            return [int(z[0]), int(z[1]), int(y[0]), int(y[1]), int(x[0]), int(x[1])]

    if all(k in entry for k in ("tz", "ty", "tx")):
        tz, ty, tx = int(entry["tz"]), int(entry["ty"]), int(entry["tx"])
        z0, y0, x0 = tz * tile_size, ty * tile_size, tx * tile_size
        return [z0, z0 + tile_size, y0, y0 + tile_size, x0, x0 + tile_size]

    tc = entry.get("tcoords")
    if isinstance(tc, dict) and all(k in tc for k in ("tz", "ty", "tx")):
        tz, ty, tx = int(tc["tz"]), int(tc["ty"]), int(tc["tx"])
        z0, y0, x0 = tz * tile_size, ty * tile_size, tx * tile_size
        return [z0, z0 + tile_size, y0, y0 + tile_size, x0, x0 + tile_size]

    raise KeyError("tile entry missing bounds (expected bounds_zyx/bounds or tz/ty/tx)")


def export_submap(
    time_name: str,
    center_zyx: Tuple[int, int, int],
    radius_vox: int,
    *,
    mode: str = "full",
    out_dir: str = "exports",
) -> Dict[str, Any]:
    """
    Export an ROI submap for a given time index.

    mode:
      - "full": decode all ROI tiles for the time
      - "delta": decode only changed ROI tiles (skip tiles that contain 'ref')

    Outputs:
      - exports/submap_<time>_<mode>_z.._y.._x.._r.. .npz
      - exports/submap_<time>_<mode>_... .json (civd.submap.v1 manifest)
    """
    if mode not in ("full", "delta"):
        raise ValueError("mode must be 'full' or 'delta'")

    os.makedirs(out_dir, exist_ok=True)

    index_path = os.path.join("data", "civd_time", time_name, "index.json")
    idx = load_index(index_path)

    # civd.index.v1
    shape_zyxc = idx["volume"]["shape_zyxc"]
    vol_shape_zyx = tuple(int(v) for v in shape_zyxc[:3])
    C = int(shape_zyxc[3])

    tile_size = int(idx["grid"]["tile_size"])
    if tile_size <= 0:
        raise KeyError("index.grid.tile_size missing/invalid (expected civd.index.v1)")

    roi = roi_from_center_radius(
        center_zyx=center_zyx,
        radius_vox=radius_vox,
        vol_shape_zyx=vol_shape_zyx,
    )

    tzr, tyr, txr = _roi_tcoord_ranges(roi, tile_size)

    # ROI output buffer
    roiZ = int(roi.z1 - roi.z0)
    roiY = int(roi.y1 - roi.y0)
    roiX = int(roi.x1 - roi.x0)
    out_vol = np.zeros((roiZ, roiY, roiX, C), dtype=np.float32)

    tiles_total = 0
    tiles_included = 0

    t0 = time.perf_counter()

    # iterate tiles from index (v1 currently: list)
    for entry in idx.get("tiles", []):
        if not isinstance(entry, dict):
            continue

        # delta mode: skip unchanged tiles
        if mode == "delta" and "ref" in entry:
            continue

        # bounds -> tcoords -> ROI membership
        b = _bounds6_from_entry(entry, tile_size=tile_size)
        z0, z1, y0, y1, x0, x1 = b
        tz = z0 // tile_size
        ty = y0 // tile_size
        tx = x0 // tile_size

        # count membership against ROI ranges
        if (tz not in tzr) or (ty not in tyr) or (tx not in txr):
            continue

        tiles_total += 1

        # decode (time_loader resolves refs if present; delta mode avoids them)
        tile_arr, _st = decode_tile_from_entry(entry, idx)

        # intersect tile bounds with ROI bounds
        iz0 = max(z0, roi.z0)
        iz1 = min(z1, roi.z1)
        iy0 = max(y0, roi.y0)
        iy1 = min(y1, roi.y1)
        ix0 = max(x0, roi.x0)
        ix1 = min(x1, roi.x1)

        if iz0 >= iz1 or iy0 >= iy1 or ix0 >= ix1:
            continue

        # offsets within tile
        sz0 = iz0 - z0
        sy0 = iy0 - y0
        sx0 = ix0 - x0
        sz1 = sz0 + (iz1 - iz0)
        sy1 = sy0 + (iy1 - iy0)
        sx1 = sx0 + (ix1 - ix0)

        # offsets within ROI buffer
        dz0 = iz0 - roi.z0
        dy0 = iy0 - roi.y0
        dx0 = ix0 - roi.x0
        dz1 = dz0 + (iz1 - iz0)
        dy1 = dy0 + (iy1 - iy0)
        dx1 = dx0 + (ix1 - ix0)

        out_vol[dz0:dz1, dy0:dy1, dx0:dx1, :] = tile_arr[sz0:sz1, sy0:sy1, sx0:sx1, :]
        tiles_included += 1

    decode_ms = (time.perf_counter() - t0) * 1000.0

    cz, cy, cx = [int(v) for v in center_zyx]
    npz_name = f"submap_{time_name}_{mode}_z{cz}_y{cy}_x{cx}_r{int(radius_vox)}.npz"
    json_name = f"submap_{time_name}_{mode}_z{cz}_y{cy}_x{cx}_r{int(radius_vox)}.json"
    npz_path = os.path.join(out_dir, npz_name)
    json_path = os.path.join(out_dir, json_name)

    np.savez_compressed(npz_path, volume=out_vol)
    bytes_npz = int(os.path.getsize(npz_path))

    meta = {
        "schema_version": SCHEMA_SUBMAP_V1,
        "time": time_name,
        "mode": mode,
        "roi": {"z0": int(roi.z0), "z1": int(roi.z1), "y0": int(roi.y0), "y1": int(roi.y1), "x0": int(roi.x0), "x1": int(roi.x1)},
        "shape_zyxc": [roiZ, roiY, roiX, int(C)],
        "tile_size": int(tile_size),
        "tiles_total": int(tiles_total),
        "tiles_included": int(tiles_included),
        "bytes_npz": int(bytes_npz),
        "decode_ms": float(decode_ms),
        "source_index": index_path.replace("\\", "/"),
        "npz_path": npz_path.replace("\\", "/"),
        "channels": [f"chan{i}" for i in range(int(C))],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    print(f"Exported: {npz_path}")
    print(f"  tiles: {tiles_included} decode_ms: {decode_ms:.2f} bytes: {bytes_npz}")

    return meta


def main() -> None:
    center = (128, 128, 160)
    r = 40
    export_submap("t000", center, r, mode="full")
    export_submap("t001", center, r, mode="full")
    export_submap("t001", center, r, mode="delta")


if __name__ == "__main__":
    main()
