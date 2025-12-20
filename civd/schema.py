from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


SCHEMA_INDEX_V1 = "civd.index.v1"


@dataclass(frozen=True)
class SchemaError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def _require(d: Dict[str, Any], key: str, ctx: str) -> Any:
    if key not in d:
        raise SchemaError(f"[{ctx}] missing required key: {key}")
    return d[key]


def _as_int_list6(bounds: Any) -> List[int]:
    """
    Normalize bounds_zyx into [z0,z1,y0,y1,x0,x1].
    Accepts:
      - list/tuple [z0,z1,y0,y1,x0,x1]
      - dict {z0,z1,y0,y1,x0,x1}
      - dict {z:[z0,z1], y:[y0,y1], x:[x0,x1]}
    """
    if isinstance(bounds, (list, tuple)) and len(bounds) == 6:
        return [int(x) for x in bounds]

    if isinstance(bounds, dict):
        if all(k in bounds for k in ("z0", "z1", "y0", "y1", "x0", "x1")):
            return [
                int(bounds["z0"]), int(bounds["z1"]),
                int(bounds["y0"]), int(bounds["y1"]),
                int(bounds["x0"]), int(bounds["x1"]),
            ]
        if all(k in bounds for k in ("z", "y", "x")):
            z, y, x = bounds["z"], bounds["y"], bounds["x"]
            if (
                isinstance(z, (list, tuple)) and len(z) == 2
                and isinstance(y, (list, tuple)) and len(y) == 2
                and isinstance(x, (list, tuple)) and len(x) == 2
            ):
                return [int(z[0]), int(z[1]), int(y[0]), int(y[1]), int(x[0]), int(x[1])]

    raise SchemaError(f"bounds_zyx not normalizable to 6-int list: got {type(bounds)} -> {bounds}")

def infer_tile_size_from_bounds(bounds6: List[int]) -> int:
    z0, z1, *_ = bounds6
    ts = int(z1 - z0)
    if ts <= 0:
        raise SchemaError(f"invalid tile_size inferred from bounds: {bounds6}")
    return ts


def verify_index_v1(idx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate an index.json matches civd.index.v1.
    Notes:
      - bounds_zyx must be the 6-int list form in v1.
      - ref.time is OPTIONAL in v1 (back-compat). If present, must be a non-empty string.
    """
    schema_version = _require(idx, "schema_version", "index")
    if schema_version != SCHEMA_INDEX_V1:
        raise SchemaError(f"[index] schema_version must be '{SCHEMA_INDEX_V1}', got '{schema_version}'")

    volume = _require(idx, "volume", "index")
    if not isinstance(volume, dict):
        raise SchemaError("[index] volume must be an object")

    shape = _require(volume, "shape_zyxc", "index.volume")
    if not (isinstance(shape, list) and len(shape) == 4):
        raise SchemaError("[index.volume] shape_zyxc must be [Z,Y,X,C]")
    Z, Y, X, C = [int(v) for v in shape]
    if min(Z, Y, X, C) <= 0:
        raise SchemaError("[index.volume] shape_zyxc must be positive")

    grid = _require(idx, "grid", "index")
    if not isinstance(grid, dict):
        raise SchemaError("[index] grid must be an object")
    tile_size = int(_require(grid, "tile_size", "index.grid"))
    if tile_size <= 0:
        raise SchemaError("[index.grid] tile_size must be > 0")

    pack = _require(idx, "pack", "index")
    if not isinstance(pack, dict):
        raise SchemaError("[index] pack must be an object")
    pack_path = _require(pack, "path", "index.pack")
    if not isinstance(pack_path, str) or not pack_path:
        raise SchemaError("[index.pack] path must be a non-empty string")

    tiles = _require(idx, "tiles", "index")
    if not isinstance(tiles, list) or len(tiles) == 0:
        raise SchemaError("[index] tiles must be a non-empty list")

    for i, e in enumerate(tiles):
        if not isinstance(e, dict):
            raise SchemaError(f"[index.tiles[{i}]] entry must be an object")

        tid = _require(e, "tile_id", f"index.tiles[{i}]")
        if not isinstance(tid, str) or not tid:
            raise SchemaError(f"[index.tiles[{i}]] tile_id must be a non-empty string")

        b6 = _as_int_list6(_require(e, "bounds_zyx", f"index.tiles[{i}]"))
        if (b6[1] - b6[0]) != tile_size:
            raise SchemaError(
                f"[index.tiles[{i}]] bounds_zyx tile size mismatch: expected {tile_size}, got {b6}"
            )

        # storage fields: either local (offset/length) or ref
        if "ref" in e:
            ref = e["ref"]
            if not isinstance(ref, dict):
                raise SchemaError(f"[index.tiles[{i}]] ref must be an object")

            if "time" in ref:
                if not isinstance(ref["time"], str) or not ref["time"]:
                    raise SchemaError(f"[index.tiles[{i}].ref] time must be a non-empty string if present")

            _require(ref, "offset", f"index.tiles[{i}].ref")
            _require(ref, "length", f"index.tiles[{i}].ref")
        else:
            _require(e, "offset", f"index.tiles[{i}]")
            _require(e, "length", f"index.tiles[{i}]")

    return idx
