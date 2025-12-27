from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

from civd.source import ObservationRequest, ObservationSource


@dataclass
class NumpyObservation:
    array: np.ndarray
    meta: Dict[str, Any]


class NumpyAdapter:
    """
    First-class adapter: returns NumPy arrays + metadata with no external deps.
    """

    def __init__(self, src: ObservationSource):
        self.src = src

    def get(self, req: ObservationRequest) -> NumpyObservation:
        pkt = self.src.observe(req)

        return NumpyObservation(
            array=pkt.volume,  # shape: (roiZ, roiY, roiX, C)
            meta={
                "schema_version": pkt.schema_version,
                "time": pkt.time,
                "mode": pkt.mode,
                "roi": pkt.roi,
                "shape_zyxc": pkt.shape_zyxc,
                "tile_size": pkt.tile_size,
                "channels": pkt.channels,
                "tiles_total": pkt.tiles_total,
                "tiles_included": pkt.tiles_included,
                "bytes_read": pkt.bytes_read,
                "decode_ms": pkt.decode_ms,
            },
        )
