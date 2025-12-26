"""
CIVD Public API (locked surface).

Only objects imported here are considered stable and supported.
Everything else in the package may change without notice.
"""

from __future__ import annotations

# Public core types
from civd.source import ROIBox, VolumePacket, Mode

# Public entrypoint
from civd.world import World

__all__ = [
    "World",
    "ROIBox",
    "VolumePacket",
    "Mode",
]

__version__ = "0.1.0"
