from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Tuple

import numpy as np

from civd.roi import ROIBox, roi_from_center_radius, roi_tiles
from civd.roi_delta import roi_delta_tiles
from civd.time_loader import load_index, decode_tile_from_entry

CIVD_VERSION = "0.1.0-core"
SUBMAP_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Stats:
    tiles_total: int
    tiles_decoded: int
    tiles_reused: int
    bytes_read_compressed: int
    bytes_out_decoded: int
    decode_ms: float


@dataclass
class Submap:
    schema_version: str
    civd_version: str
    time: str
    roi: ROIBox
    mode: Literal["full", "delta"]
    tile_size: int
    shape_zyxc: Tuple[int, int, int, int]
    tiles: Dict[str, np.ndarray]
    tile_bounds_zyx: Dict[str, Tuple[int, int, int, int, int, int]]


class World:
    """
    CIVD Core API v1 surface.
    Stable, schema-tolerant, dependency-light.
    """

    def __init__(self, root: str, *, mode: Literal["r", "rw"] = "r", default_tile_size: int = 32):
        self.root = root
        self.mode = mode
        self.default_tile_size = int(default_tile_size)
        self._time_index_cache: Dict[str, dict] = {}

    @staticmethod
    def open(root: str, *, mode: Literal["r", "rw"] = "r", default_tile_size: int = 32) -> "World":
        return World(root, mode=mode, default_tile_size=default_tile_size)

    # ---------- index helpers ----------

    def _shape_zyxc_from_index(self, idx: dict) -> Tuple[int, int, int, int]:
        vol = idx.get("volume")
        if isinstance(vol, dict) and "shape_zyxc" in vol:
            return tuple(vol["shape_zyxc"])
        if "shape_zyxc" in idx:
            return tuple(idx["shape_zyxc"])
        raise KeyError("shape_zyxc not found in index")

    def _pack_path_from_index(self, idx: dict) -> str:
        pack = idx.get("pack")
        if isinstance(pack, dict) and "path" in pack:
            return pack["path"]
        if "pack_path" in idx:
            return idx["pack_path"]
        raise KeyError("pack path not found in index")

    def _tile_size_from_index(self, idx: dict) -> int:
        if "tile_size" in idx:
            return int(idx["tile_size"])

        grid = idx.get("grid")
        if isinstance(grid, dict) and "tile_size" in grid:
            return int(grid["tile_size"])

        tiles_meta = idx.get("tiles")
        if isinstance(tiles_meta, dict) and "tile_size" in tiles_meta:
            return int(tiles_meta["tile_size"])

        return self.default_tile_size

    def _bounds_from_entry(self, e: dict, *, tile_size: int) -> Tuple[int, int, int, int, int, int]:
        """Return bounds_zyx as (z0,z1,y0,y1,x0,x1) across schema variants.

        Supports:
          - list/tuple of 6 ints
          - dict forms: {'z0':..,'z1':..,'y0':..,'y1':..,'x0':..,'x1':..}
          - dict forms: {'z': [z0,z1], 'y':[y0,y1], 'x':[x0,x1]}
          - explicit z0/z1/y0/y1/x0/x1 fields
          - infer from tile_id (z##_y##_x##) and tile_size
        """
        b = e.get("bounds_zyx") or e.get("bounds") or e.get("bounds_zyx6")

        # list/tuple style
        if isinstance(b, (list, tuple)) and len(b) == 6:
            return (int(b[0]), int(b[1]), int(b[2]), int(b[3]), int(b[4]), int(b[5]))

        # dict style: z0..x1
        if isinstance(b, dict):
            if all(k in b for k in ("z0","z1","y0","y1","x0","x1")):
                return (int(b["z0"]), int(b["z1"]), int(b["y0"]), int(b["y1"]), int(b["x0"]), int(b["x1"]))
            if all(k in b for k in ("z","y","x")):
                z = b["z"]; y = b["y"]; x = b["x"]
                if isinstance(z, (list, tuple)) and isinstance(y, (list, tuple)) and isinstance(x, (list, tuple)):
                    return (int(z[0]), int(z[1]), int(y[0]), int(y[1]), int(x[0]), int(x[1]))

        # explicit fields on entry
        if all(k in e for k in ("z0","z1","y0","y1","x0","x1")):
            return (int(e["z0"]), int(e["z1"]), int(e["y0"]), int(e["y1"]), int(e["x0"]), int(e["x1"]))

        # infer from tile_id like z03_y03_x04
        tid = e.get("tile_id") or e.get("id") or e.get("tile")
        if isinstance(tid, str):
            import re
            m = re.match(r"z(\d+)_y(\d+)_x(\d+)", tid)
            if m:
                tz, ty, tx = map(int, m.groups())
                z0, y0, x0 = tz * tile_size, ty * tile_size, tx * tile_size
                return (z0, z0 + tile_size, y0, y0 + tile_size, x0, x0 + tile_size)

        raise KeyError("No bounds fields in entry and cannot infer from tile_id")

    # ---------- metadata ----------

    def index_path(self, time: str) -> str:
        if self.root in ("", "."):
            return f"data/civd_time/{time}/index.json"
        return f"{self.root}/data/civd_time/{time}/index.json"

    def load_time_index(self, time: str) -> dict:
        if time not in self._time_index_cache:
            self._time_index_cache[time] = load_index(self.index_path(time))
        return self._time_index_cache[time]

    def meta(self, time: str = "t000") -> dict:
        idx = self.load_time_index(time)
        shape = self._shape_zyxc_from_index(idx)
        return {
            "civd_version": CIVD_VERSION,
            "schema_version": idx.get("schema_version", "unknown"),
            "time": time,
            "shape_zyxc": shape,
            "tile_size": self._tile_size_from_index(idx),
            "channels": shape[3],
            "pack_path": self._pack_path_from_index(idx),
        }

    # ---------- ROI helpers ----------

    def roi_from_center_radius(
        self,
        *,
        zyx_center: Tuple[int, int, int],
        radius_vox: int,
        time: str = "t000",
    ) -> ROIBox:
        idx = self.load_time_index(time)
        shape = self._shape_zyxc_from_index(idx)
        Z, Y, X, _ = shape
        return roi_from_center_radius(
            center_zyx=zyx_center,
            radius_vox=radius_vox,
            vol_shape_zyx=(Z, Y, X),
        )

    # ---------- core load ----------

    def load_roi_tiles(
        self,
        *,
        time: str,
        roi: ROIBox,
        mode: Literal["full", "delta"] = "full",
    ) -> Tuple[Submap, Stats]:
        import time as _time

        idx = self.load_time_index(time)
        pack_path = self._pack_path_from_index(idx)
        tile_size = self._tile_size_from_index(idx)
        shape_zyxc = self._shape_zyxc_from_index(idx)

        entries = roi_tiles(idx, roi) if mode == "full" else roi_delta_tiles(idx, roi)

        t0 = _time.perf_counter()
        tiles: Dict[str, np.ndarray] = {}
        tile_bounds: Dict[str, Tuple[int, int, int, int, int, int]] = {}
        bytes_read = 0
        bytes_out = 0

        for e in entries:
            tid = e.get("tile_id") or e.get("id") or e.get("tile")
            if tid is None:
                raise KeyError("Entry missing tile_id/id/tile")
            tid = str(tid)

            if "ref" in e and isinstance(e["ref"], dict) and "length" in e["ref"]:
                bytes_read += int(e["ref"]["length"])
            elif "length" in e:
                bytes_read += int(e["length"])

            arr, _st = decode_tile_from_entry(e, idx)
            tiles[tid] = arr
            bytes_out += arr.nbytes

            tile_bounds[tid] = self._bounds_from_entry(e, tile_size=tile_size)

        t1 = _time.perf_counter()

        stats = Stats(
            tiles_total=len(entries),
            tiles_decoded=len(entries),
            tiles_reused=0,
            bytes_read_compressed=bytes_read,
            bytes_out_decoded=bytes_out,
            decode_ms=(t1 - t0) * 1000.0,
        )

        submap = Submap(
            schema_version=SUBMAP_SCHEMA_VERSION,
            civd_version=CIVD_VERSION,
            time=time,
            roi=roi,
            mode=mode,
            tile_size=tile_size,
            shape_zyxc=shape_zyxc,
            tiles=tiles,
            tile_bounds_zyx=tile_bounds,
        )

        return submap, stats

    # ---------- replay ----------

    @staticmethod
    def replay(
        base_roi: np.ndarray,
        *,
        submap_tiles: Dict[str, np.ndarray],
        tile_bounds_zyx: Dict[str, Tuple[int, int, int, int, int, int]],
        roi: ROIBox,
    ) -> np.ndarray:
        out = np.array(base_roi, copy=True)

        for tid, tile in submap_tiles.items():
            z0, z1, y0, y1, x0, x1 = tile_bounds_zyx[tid]

            iz0 = max(z0, roi.z0)
            iz1 = min(z1, roi.z1)
            iy0 = max(y0, roi.y0)
            iy1 = min(y1, roi.y1)
            ix0 = max(x0, roi.x0)
            ix1 = min(x1, roi.x1)
            if iz0 >= iz1 or iy0 >= iy1 or ix0 >= ix1:
                continue

            rz0, rz1 = iz0 - roi.z0, iz1 - roi.z0
            ry0, ry1 = iy0 - roi.y0, iy1 - roi.y0
            rx0, rx1 = ix0 - roi.x0, ix1 - roi.x0

            tz0, tz1 = iz0 - z0, iz1 - z0
            ty0, ty1 = iy0 - y0, iy1 - y0
            tx0, tx1 = ix0 - x0, ix1 - x0

            out[rz0:rz1, ry0:ry1, rx0:rx1, :] = tile[
                tz0:tz1, ty0:ty1, tx0:tx1, :
            ]

        return out
