import json
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ROIBox:
    """
    Axis-aligned ROI in voxel coordinates (not tile coordinates).

    (z0,z1), (y0,y1), (x0,x1) are half-open ranges: [start, end)
    """
    z0: int
    z1: int
    y0: int
    y1: int
    x0: int
    x1: int


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def roi_from_center_radius(center_zyx: Tuple[int, int, int], radius_vox: int, vol_shape_zyx: Tuple[int, int, int]) -> ROIBox:
    """
    Builds an axis-aligned ROI box centered at center_zyx with +/- radius_vox in each axis.
    Clamped to the volume.
    """
    cz, cy, cx = center_zyx
    Z, Y, X = vol_shape_zyx

    z0 = _clamp(cz - radius_vox, 0, Z)
    z1 = _clamp(cz + radius_vox, 0, Z)
    y0 = _clamp(cy - radius_vox, 0, Y)
    y1 = _clamp(cy + radius_vox, 0, Y)
    x0 = _clamp(cx - radius_vox, 0, X)
    x1 = _clamp(cx + radius_vox, 0, X)

    # ensure non-empty (at least 1 voxel thick in each dim)
    if z1 <= z0:
        z1 = min(Z, z0 + 1)
    if y1 <= y0:
        y1 = min(Y, y0 + 1)
    if x1 <= x0:
        x1 = min(X, x0 + 1)

    return ROIBox(z0, z1, y0, y1, x0, x1)


def roi_tiles(index: Dict, roi: ROIBox) -> List[Dict]:
    """
    Returns the tile entries from index['tiles'] that intersect the ROI.
    Uses fast coordinate math (tile grid), not scanning the entire pack.

    Intersection rule: tile bounds overlap ROI bounds in all 3 axes.
    """
    ts = index["tile_spec"]
    tz, ty, tx = ts["tile_z"], ts["tile_y"], ts["tile_x"]

    grid = index["grid"]
    nz, ny, nx = grid["nz"], grid["ny"], grid["nx"]

    # Convert ROI voxel bounds to inclusive tile coordinate ranges
    # Using half-open intervals:
    # start tile = floor(start / tile_size)
    # end tile = ceil(end / tile_size) - 1
    tz0 = roi.z0 // tz
    ty0 = roi.y0 // ty
    tx0 = roi.x0 // tx

    tz1 = (roi.z1 + tz - 1) // tz - 1
    ty1 = (roi.y1 + ty - 1) // ty - 1
    tx1 = (roi.x1 + tx - 1) // tx - 1

    # Clamp tile coords to grid
    tz0 = _clamp(tz0, 0, nz - 1)
    ty0 = _clamp(ty0, 0, ny - 1)
    tx0 = _clamp(tx0, 0, nx - 1)

    tz1 = _clamp(tz1, 0, nz - 1)
    ty1 = _clamp(ty1, 0, ny - 1)
    tx1 = _clamp(tx1, 0, nx - 1)

    # Build a lookup from (tz,ty,tx) -> tile entry for O(1) access
    # This avoids scanning all tiles each query.
    lookup = {}
    for t in index["tiles"]:
        c = t["tile_coords"]
        lookup[(c["tz"], c["ty"], c["tx"])] = t

    hits: List[Dict] = []
    for a in range(tz0, tz1 + 1):
        for b in range(ty0, ty1 + 1):
            for c in range(tx0, tx1 + 1):
                entry = lookup.get((a, b, c))
                if entry is not None:
                    hits.append(entry)

    # Deterministic ordering
    hits.sort(key=lambda e: (e["tile_coords"]["tz"], e["tile_coords"]["ty"], e["tile_coords"]["tx"]))
    return hits


def load_index(path: str = "data/civd_tiles/index.json") -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    idx = load_index()
    vol = idx["volume"]["shape_zyxc"]
    Z, Y, X, _ = vol

    # Example ROI: center of the world, radius 40 voxels
    roi = roi_from_center_radius((Z // 2, Y // 2, X // 2), radius_vox=40, vol_shape_zyx=(Z, Y, X))
    tiles = roi_tiles(idx, roi)

    print("ROI:", roi)
    print("ROI tiles:", len(tiles))
    if tiles:
        print("First tile:", tiles[0]["tile_id"], tiles[0]["tile_coords"])
        print("Last tile: ", tiles[-1]["tile_id"], tiles[-1]["tile_coords"])
