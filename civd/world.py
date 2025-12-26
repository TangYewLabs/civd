from __future__ import annotations

import os
import time as _time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal

import numpy as np

def _tile_id_from_entry(entry: Dict[str, Any], *, tile_size: int) -> Optional[str]:
    """
    Return canonical tile id like z02_y03_x04 from a tile entry.
    Works even when 'id' is missing by using tz/ty/tx, tcoords, or bounds.
    """
    tid = entry.get("id")
    if isinstance(tid, str) and tid:
        return tid

    if all(k in entry for k in ("tz", "ty", "tx")):
        return _tile_id_from_tcoords(int(entry["tz"]), int(entry["ty"]), int(entry["tx"]))

    tc = entry.get("tcoords")
    if isinstance(tc, dict) and all(k in tc for k in ("tz", "ty", "tx")):
        return _tile_id_from_tcoords(int(tc["tz"]), int(tc["ty"]), int(tc["tx"]))

    b = entry.get("bounds_zyx", entry.get("bounds"))
    if isinstance(b, (list, tuple)) and len(b) == 6:
        z0, _, y0, _, x0, _ = [int(v) for v in b]
        return _tile_id_from_tcoords(z0 // tile_size, y0 // tile_size, x0 // tile_size)

    if isinstance(b, dict) and all(k in b for k in ("z0", "y0", "x0")):
        return _tile_id_from_tcoords(int(b["z0"]) // tile_size, int(b["y0"]) // tile_size, int(b["x0"]) // tile_size)

    return None


def _has_own_payload(entry: Dict[str, Any]) -> bool:
    """
    True if this tile entry contains actual payload data
    for the current time index (i.e. should be included in delta).
    """
    if isinstance(entry.get("offset"), int) and isinstance(entry.get("length"), int):
        return True

    payload = entry.get("payload")
    if isinstance(payload, dict):
        if isinstance(payload.get("offset"), int) and isinstance(payload.get("length"), int):
            return True

    return False

from civd.source import ROIBox, VolumePacket, Mode

# Reuse your existing loader utilities:
from civd.time_loader import load_index, decode_tile_from_entry


PACKET_SCHEMA_V1 = "civd.packet.v1"


def _index_path(root: str, time_name: str) -> str:
    # supports root="." or "" or explicit path
    if root in ("", "."):
        return os.path.join("data", "civd_time", time_name, "index.json")
    return os.path.join(root, "data", "civd_time", time_name, "index.json")


def _tile_size_from_index(idx: Dict[str, Any]) -> int:
    # civd.index.v1: idx["grid"]["tile_size"]
    grid = idx.get("grid", {})
    ts = int(grid.get("tile_size", 0))
    if ts <= 0:
        raise KeyError("index.grid.tile_size missing or invalid")
    return ts


def _shape_zyxc_from_index(idx: Dict[str, Any]) -> Tuple[int, int, int, int]:
    vol = idx.get("volume", {})
    shape = vol.get("shape_zyxc")
    if not (isinstance(shape, list) and len(shape) == 4):
        raise KeyError("index.volume.shape_zyxc missing/invalid")
    z, y, x, c = (int(shape[0]), int(shape[1]), int(shape[2]), int(shape[3]))
    return (z, y, x, c)


def _bounds6_from_entry(entry: Dict[str, Any], *, tile_size: int) -> Tuple[int, int, int, int, int, int]:
    """
    Return (z0,z1,y0,y1,x0,x1) tolerant to schema variants.
    """
    b = entry.get("bounds_zyx", entry.get("bounds"))
    if isinstance(b, (list, tuple)) and len(b) == 6:
        z0, z1, y0, y1, x0, x1 = [int(v) for v in b]
        return (z0, z1, y0, y1, x0, x1)

    if isinstance(b, dict) and all(k in b for k in ("z0", "z1", "y0", "y1", "x0", "x1")):
        return (int(b["z0"]), int(b["z1"]), int(b["y0"]), int(b["y1"]), int(b["x0"]), int(b["x1"]))

    # Derive from tz/ty/tx
    if all(k in entry for k in ("tz", "ty", "tx")):
        tz, ty, tx = int(entry["tz"]), int(entry["ty"]), int(entry["tx"])
        z0, y0, x0 = tz * tile_size, ty * tile_size, tx * tile_size
        return (z0, z0 + tile_size, y0, y0 + tile_size, x0, x0 + tile_size)

    tc = entry.get("tcoords")
    if isinstance(tc, dict) and all(k in tc for k in ("tz", "ty", "tx")):
        tz, ty, tx = int(tc["tz"]), int(tc["ty"]), int(tc["tx"])
        z0, y0, x0 = tz * tile_size, ty * tile_size, tx * tile_size
        return (z0, z0 + tile_size, y0, y0 + tile_size, x0, x0 + tile_size)

    raise KeyError("tile entry missing bounds (bounds_zyx/bounds or tz/ty/tx)")


def _roi_tcoord_ranges(roi: ROIBox, tile_size: int) -> Tuple[range, range, range]:
    tz0 = int(roi.z0) // tile_size
    tz1 = (int(roi.z1) - 1) // tile_size
    ty0 = int(roi.y0) // tile_size
    ty1 = (int(roi.y1) - 1) // tile_size
    tx0 = int(roi.x0) // tile_size
    tx1 = (int(roi.x1) - 1) // tile_size
    return (range(tz0, tz1 + 1), range(ty0, ty1 + 1), range(tx0, tx1 + 1))


def _tile_id_from_tcoords(tz: int, ty: int, tx: int) -> str:
    # padded to match your existing naming
    return f"z{tz:02d}_y{ty:02d}_x{tx:02d}"


class World:
    """
    CIVD World implements the locked ObservationSource contract.
    """

    def __init__(self, root: str = ".", *, mode: Literal["r", "rw"] = "r"):
        self.root = root
        self.mode = mode
        self._cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def open(root: str = ".", *, mode: Literal["r", "rw"] = "r") -> "World":
        return World(root, mode=mode)

    def load_time_index(self, time_name: str) -> Dict[str, Any]:
        if time_name not in self._cache:
            self._cache[time_name] = load_index(_index_path(self.root, time_name))
        return self._cache[time_name]

    def meta(self, time: str = "t000") -> Dict[str, Any]:
        idx = self.load_time_index(time_name)
        z, y, x, c = _shape_zyxc_from_index(idx)
        return {
            "schema_version": idx.get("schema_version", "unknown"),
            "time": time,
            "shape_zyxc": (z, y, x, c),
            "tile_size": _tile_size_from_index(idx),
            "pack": idx.get("pack", {}),
        }

    def query(
        self,
        time_name: str,
        roi: ROIBox,
        channels: Optional[Sequence[int]] = None,
        mode: Mode = "full",
    ) -> VolumePacket:

        if mode not in ("full", "delta"):
            raise ValueError("mode must be 'full' or 'delta'")

        idx = self.load_time_index(time_name)
        tile_size = _tile_size_from_index(idx)
        Z, Y, X, C = _shape_zyxc_from_index(idx)

        # clamp ROI
        roi = ROIBox(
            z0=max(0, int(roi.z0)), z1=min(Z, int(roi.z1)),
            y0=max(0, int(roi.y0)), y1=min(Y, int(roi.y1)),
            x0=max(0, int(roi.x0)), x1=min(X, int(roi.x1)),
        )

        roiZ, roiY, roiX = roi.shape_zyx
        if channels is None:
            chan_idx = list(range(C))
        else:
            chan_idx = [int(i) for i in channels]
        outC = len(chan_idx)

        out = np.zeros((roiZ, roiY, roiX, outC), dtype=np.float32)

        tzr, tyr, txr = _roi_tcoord_ranges(roi, tile_size)
        roi_tile_ids = [_tile_id_from_tcoords(tz, ty, tx) for tz in tzr for ty in tyr for tx in txr]
        tiles_total = len(roi_tile_ids)

        # Build quick lookup from id -> entry.
        # Your civd.index.v1 currently has idx["tiles"] as a list of dict entries.
        tile_entries: List[Dict[str, Any]] = [e for e in idx.get("tiles", []) if isinstance(e, dict)]
        by_id: Dict[str, Dict[str, Any]] = {}

        for e in tile_entries:
            tid = _tile_id_from_entry(e, tile_size=tile_size)
            if tid:
                by_id[tid] = e

        tiles_included = 0
        bytes_read = 0

        t0 = _time.perf_counter()

        for tid in roi_tile_ids:
            e = by_id.get(tid)
            if e is None:
                # not fatal: some indices may not store explicit ids
                continue

            # delta mode: skip tiles that are only refs (unchanged)
            if mode == "delta" and not _has_own_payload(e):
                continue

            tile_arr, st = decode_tile_from_entry(e, idx)
            tiles_included += 1
            if isinstance(st, dict):
                bytes_read += int(st.get("bytes_read", 0))

            z0, z1, y0, y1, x0, x1 = _bounds6_from_entry(e, tile_size=tile_size)

            # intersection in world coords
            iz0, iz1 = max(z0, roi.z0), min(z1, roi.z1)
            iy0, iy1 = max(y0, roi.y0), min(y1, roi.y1)
            ix0, ix1 = max(x0, roi.x0), min(x1, roi.x1)
            if iz0 >= iz1 or iy0 >= iy1 or ix0 >= ix1:
                continue

            # offsets within tile
            sz0, sy0, sx0 = iz0 - z0, iy0 - y0, ix0 - x0
            sz1, sy1, sx1 = sz0 + (iz1 - iz0), sy0 + (iy1 - iy0), sx0 + (ix1 - ix0)

            # offsets within ROI buffer
            dz0, dy0, dx0 = iz0 - roi.z0, iy0 - roi.y0, ix0 - roi.x0
            dz1, dy1, dx1 = dz0 + (iz1 - iz0), dy0 + (iy1 - iy0), dx0 + (ix1 - ix0)

            # select channels
            out[dz0:dz1, dy0:dy1, dx0:dx1, :] = tile_arr[sz0:sz1, sy0:sy1, sx0:sx1, :][:, :, :, chan_idx]

        decode_ms = (_time.perf_counter() - t0) * 1000.0

        packet = VolumePacket(
            schema_version=PACKET_SCHEMA_V1,
            time=time_name,
            mode=mode,
            roi=roi,
            shape_zyxc=(roiZ, roiY, roiX, outC),
            tile_size=tile_size,
            channels=[f"chan{i}" for i in chan_idx],
            tiles_total=tiles_total,
            tiles_included=tiles_included,
            bytes_read=int(bytes_read),
            decode_ms=float(decode_ms),
            volume=out,
            tile_mask=None,
            meta={"index_schema_version": idx.get("schema_version", "unknown")},
        )
        return packet

    def apply_delta(self, *, base: VolumePacket, delta: VolumePacket) -> VolumePacket:
        # v1 rule: ROI + channels must match to apply delta deterministically
        if base.roi != delta.roi:
            raise ValueError("apply_delta requires identical ROIBox")
        if base.shape_zyxc != delta.shape_zyxc:
            raise ValueError("apply_delta requires identical shape_zyxc")
        if base.channels != delta.channels:
            raise ValueError("apply_delta requires identical channels ordering")

        out = np.array(base.volume, copy=True)

        # If delta is sparse, we apply “overwrite nonzero” rule in v1.
        # This is conservative and deterministic; later you can add tile_mask-based patching.
        mask = delta.volume != 0
        out[mask] = delta.volume[mask]

        return VolumePacket(
            schema_version=base.schema_version,
            time=delta.time,
            mode="full",
            roi=base.roi,
            shape_zyxc=base.shape_zyxc,
            tile_size=base.tile_size,
            channels=base.channels,
            tiles_total=base.tiles_total,
            tiles_included=base.tiles_total,
            bytes_read=base.bytes_read + delta.bytes_read,
            decode_ms=base.decode_ms + delta.decode_ms,
            volume=out,
            tile_mask=None,
            meta={"applied_delta_from": base.time, "delta_time": delta.time},
        )
