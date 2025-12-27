from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

from civd.source import ObservationRequest, ObservationSource

try:
    import torch
except Exception:  # pragma: no cover
    torch = None  # type: ignore


@dataclass
class TorchObservation:
    """
    Torch observation product (adapter-level output).
    """
    tensor: "torch.Tensor"
    meta: Dict[str, Any]


class TorchAdapter:
    """
    Adapter: CIVD ObservationSource -> torch.Tensor

    Default layout: (Z, Y, X, C)
    Optional: channels_first -> (C, Z, Y, X)
    """

    def __init__(
        self,
        source: ObservationSource,
        *,
        device: Optional[str] = None,
        dtype: str = "float32",
        channels_first: bool = False,
        copy: bool = True,
    ) -> None:
        self.source = source
        self.device = device
        self.dtype = dtype
        self.channels_first = channels_first
        self.copy = copy

        if torch is None:
            raise ImportError(
                "TorchAdapter requires PyTorch. Install with: pip install torch"
            )

        if not hasattr(torch, self.dtype):
            raise ValueError(f"Unknown torch dtype: {self.dtype!r}")

    def get(self, req: ObservationRequest) -> TorchObservation:
        pkt = self.source.observe(req)
        arr = pkt.volume  # numpy array (Z,Y,X,C)

        if self.copy:
            t = torch.from_numpy(np.ascontiguousarray(arr)).clone()
        else:
            t = torch.from_numpy(arr)

        t = t.to(getattr(torch, self.dtype))

        if self.channels_first:
            t = t.permute(3, 0, 1, 2).contiguous()

        if self.device is not None:
            t = t.to(self.device)

        meta = {
            "time_name": pkt.time,
            "mode": pkt.mode,
            "shape_zyxc": pkt.shape_zyxc,
            "tile_size": pkt.tile_size,
            "tiles_total": pkt.tiles_total,
            "tiles_included": pkt.tiles_included,
            "bytes_read": pkt.bytes_read,
            "decode_ms": pkt.decode_ms,
            "channels": pkt.channels,
        }

        return TorchObservation(tensor=t, meta=meta)
