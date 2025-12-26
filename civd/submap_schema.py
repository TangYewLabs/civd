from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


SCHEMA_SUBMAP_V1 = "civd.submap.v1"


@dataclass(frozen=True)
class SubmapSchemaError(Exception):
    message: str
    def __str__(self) -> str:
        return self.message


def _req(d: Dict[str, Any], k: str, ctx: str) -> Any:
    if k not in d:
        raise SubmapSchemaError(f"[{ctx}] missing required key: {k}")
    return d[k]


def _req_int(d: Dict[str, Any], k: str, ctx: str) -> int:
    v = _req(d, k, ctx)
    try:
        return int(v)
    except Exception:
        raise SubmapSchemaError(f"[{ctx}] {k} must be int-like, got {type(v)} -> {v}")


def _req_float(d: Dict[str, Any], k: str, ctx: str) -> float:
    v = _req(d, k, ctx)
    try:
        return float(v)
    except Exception:
        raise SubmapSchemaError(f"[{ctx}] {k} must be float-like, got {type(v)} -> {v}")


def verify_submap_v1(m: Dict[str, Any]) -> Dict[str, Any]:
    sv = _req(m, "schema_version", "submap")
    if sv != SCHEMA_SUBMAP_V1:
        raise SubmapSchemaError(f"[submap] schema_version must be '{SCHEMA_SUBMAP_V1}', got '{sv}'")

    time = _req(m, "time", "submap")
    if not isinstance(time, str) or not time:
        raise SubmapSchemaError("[submap] time must be a non-empty string")

    mode = _req(m, "mode", "submap")
    if mode not in ("full", "delta"):
        raise SubmapSchemaError("[submap] mode must be 'full' or 'delta'")

    roi = _req(m, "roi", "submap")
    if not isinstance(roi, dict):
        raise SubmapSchemaError("[submap] roi must be an object")
    for k in ("z0","z1","y0","y1","x0","x1"):
        _req_int(roi, k, "submap.roi")

    shape = _req(m, "shape_zyxc", "submap")
    if not (isinstance(shape, list) and len(shape) == 4):
        raise SubmapSchemaError("[submap] shape_zyxc must be [Z,Y,X,C]")
    Z, Y, X, C = [int(x) for x in shape]
    if min(Z, Y, X, C) <= 0:
        raise SubmapSchemaError("[submap] shape_zyxc must be positive")

    tile_size = _req_int(m, "tile_size", "submap")
    if tile_size <= 0:
        raise SubmapSchemaError("[submap] tile_size must be > 0")

    tiles_total = _req_int(m, "tiles_total", "submap")
    tiles_included = _req_int(m, "tiles_included", "submap")
    if tiles_total <= 0 or tiles_included <= 0:
        raise SubmapSchemaError("[submap] tiles_total and tiles_included must be > 0")
    if tiles_included > tiles_total:
        raise SubmapSchemaError("[submap] tiles_included cannot exceed tiles_total")

    _req_int(m, "bytes_npz", "submap")
    _req_float(m, "decode_ms", "submap")

    npz_path = _req(m, "npz_path", "submap")
    if not isinstance(npz_path, str) or not npz_path:
        raise SubmapSchemaError("[submap] npz_path must be a non-empty string")

    src = _req(m, "source_index", "submap")
    if not isinstance(src, str) or not src:
        raise SubmapSchemaError("[submap] source_index must be a non-empty string")

    channels = _req(m, "channels", "submap")
    if not isinstance(channels, list) or len(channels) == 0:
        raise SubmapSchemaError("[submap] channels must be a non-empty list")

    return m
