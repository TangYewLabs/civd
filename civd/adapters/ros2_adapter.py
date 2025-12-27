from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

from civd.source import ObservationRequest, ObservationSource


@dataclass
class ROS2Observation:
    """
    ROS2-ready payload (no hard dependency on rclpy).
    You can later map this to PointCloud2, Image, or custom msgs.
    """
    payload: Dict[str, Any]


class ROS2Adapter:
    """
    First-class ROS2 adapter surface that stays dependency-light.
    """
    def __init__(self, src: ObservationSource, *, frame_id: str = "map"):
        self.src = src
        self.frame_id = frame_id

    def get(self, req: ObservationRequest) -> ROS2Observation:
        pkt = self.src.observe(req)

        # Minimal, practical payload:
        # - volume as numpy
        # - ROI as bounds
        # - timing stats
        payload = {
            "frame_id": self.frame_id,
            "time_name": pkt.time,
            "mode": pkt.mode,
            "roi": {
                "z0": int(pkt.roi.z0), "z1": int(pkt.roi.z1),
                "y0": int(pkt.roi.y0), "y1": int(pkt.roi.y1),
                "x0": int(pkt.roi.x0), "x1": int(pkt.roi.x1),
            },
            "shape_zyxc": pkt.shape_zyxc,
            "channels": pkt.channels,
            "tiles_included": pkt.tiles_included,
            "bytes_read": pkt.bytes_read,
            "decode_ms": pkt.decode_ms,
            "volume": pkt.volume,  # numpy array
        }

        return ROS2Observation(payload=payload)
