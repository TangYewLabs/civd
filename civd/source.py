from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Protocol, Sequence, Tuple

import numpy as np


SchemaName = str
Mode = Literal["full", "delta"]


@dataclass(frozen=True)
class ROIBox:
    z0: int
    z1: int
    y0: int
    y1: int
    x0: int
    x1: int

    @property
    def shape_zyx(self) -> Tuple[int, int, int]:
        return (self.z1 - self.z0, self.y1 - self.y0, self.x1 - self.x0)


@dataclass
class VolumePacket:
    """
    Canonical CIVD v1 data product.

    Meaning:
      - volume is ALWAYS ROI-local array shaped (roiZ, roiY, roiX, C)
      - mode="delta" means unchanged regions may be zeros AND tile_mask indicates which tiles are present
      - bytes_read/decode_ms are *observability* metrics, not correctness dependencies
    """

    schema_version: SchemaName  # e.g., "civd.packet.v1"
    time: str                   # e.g., "t000", "t001"
    mode: Mode                  # "full" or "delta"

    roi: ROIBox                 # world-space ROI
    shape_zyxc: Tuple[int, int, int, int]
    tile_size: int
    channels: List[str]

    tiles_total: int
    tiles_included: int

    bytes_read: int
    decode_ms: float

    volume: np.ndarray          # float32 recommended, shape (roiZ, roiY, roiX, C)
    tile_mask: Optional[np.ndarray] = None  # optional: bool mask of tiles included in ROI

    meta: Dict[str, Any] = None  # optional extra metadata


class ObservationSource(Protocol):
    """
    Locked contract for any CIVD data source.

    Downstream adapters depend ONLY on this contract.
    """

    def meta(self, time: str = "t000") -> Dict[str, Any]:
        ...

    def query(
        self,
        *,
        time: str,
        roi: ROIBox,
        channels: Optional[Sequence[int]] = None,
        mode: Mode = "full",
    ) -> VolumePacket:
        ...

    def apply_delta(self, *, base: VolumePacket, delta: VolumePacket) -> VolumePacket:
        ...
