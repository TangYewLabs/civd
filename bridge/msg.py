from dataclasses import dataclass
from typing import List, Tuple, Literal, Optional
import numpy as np


Mode = Literal["full", "delta"]


@dataclass
class SubmapDeltaMsg:
    schema: str
    timestamp: str
    mode: Mode

    # ROI bounds in Z,Y,X
    roi_zyx: Tuple[int, int, int, int, int, int]

    # One entry per tile
    tile_bounds_zyx: np.ndarray  # shape (N,6) int32
    tiles: np.ndarray            # shape (N,tz,ty,tx,C) float32

    # Optional debug/meta
    compressed_bytes_read_est: Optional[int] = None
    decode_ms: Optional[float] = None
