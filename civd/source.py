from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Protocol, Sequence, Tuple

import numpy as np

SchemaName = str
Mode = Literal["full", "delta"]

PACKET_SCHEMA_V1: SchemaName = "civd.packet.v1"


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
    Canonical CIVD packet (public, stable).

    - volume is ROI-local array shaped (roiZ, roiY, roiX, C)
    - mode="delta" means unchanged regions may be zeros; tile_mask can mark included tiles
    - bytes_read/decode_ms are observability metrics
    """

    schema_version: SchemaName  # e.g., PACKET_SCHEMA_V1
    time: str                   # e.g., "t000", "t001"
    mode: Mode                  # "full" or "delta"

    roi: ROIBox
    shape_zyxc: Tuple[int, int, int, int]
    tile_size: int
    channels: List[str]

    tiles_total: int
    tiles_included: int

    bytes_read: int
    decode_ms: float

    volume: np.ndarray
    tile_mask: Optional[np.ndarray] = None

    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def roi_shape_zyx(self) -> Tuple[int, int, int]:
        z, y, x, _c = self.shape_zyxc
        return (z, y, x)

    @property
    def channel_count(self) -> int:
        return int(self.shape_zyxc[3])


@dataclass(frozen=True)
class ObservationRequest:
    """
    Stable request surface for downstream adapters/software.
    """
    time_name: str
    roi: ROIBox
    channels: Optional[Sequence[int]] = None
    mode: Mode = "full"


class ObservationSource(Protocol):
    """
    Stable interface: adapters depend ONLY on this contract.
    """
    def observe(self, req: ObservationRequest) -> VolumePacket:
        ...


class CivdObservationSource:
    """
    Concrete ObservationSource backed by CIVD World.
    Wrapper exists to keep the ObservationSource contract stable even if World evolves.
    """
    def __init__(self, world: Any):
        self._world = world

    def observe(self, req: ObservationRequest) -> VolumePacket:
        return self._world.query(
            time_name=req.time_name,
            roi=req.roi,
            channels=req.channels,
            mode=req.mode,
        )
