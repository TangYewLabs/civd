from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

import numpy as np

from civd.source import ObservationRequest, ObservationSource


TorchDType = Union[str, "torch.dtype"]


@dataclass
class TorchObservation:
    tensor: "torch.Tensor"
    meta: Dict[str, Any]

    @property
    def array(self) -> "torch.Tensor":
        """
        Alias for consistency with other adapters that expose `.array`.
        """
        return self.tensor


class TorchAdapter:
    """
    First-class PyTorch adapter.

    Optional dependency: torch
      pip install .[torch]
      or install torch from PyTorch’s official instructions.

    Behavior:
      - Produces a tensor shaped (roiZ, roiY, roiX, C)
      - Default: CPU tensor, dtype inferred from numpy (float32)
      - If device/dtype provided, moves/converts accordingly
    """

    def __init__(
        self,
        src: ObservationSource,
        *,
        device: Optional[str] = None,
        dtype: Optional[TorchDType] = None,
    ):
        self.src = src
        self.device = device
        self.dtype = dtype

    def get(self, req: ObservationRequest) -> TorchObservation:
        try:
            import torch
        except Exception as e:
            raise RuntimeError(
                "TorchAdapter requires 'torch'. Install with: pip install .[torch] "
                "(or install torch via official PyTorch instructions)."
            ) from e

        pkt = self.src.observe(req)
        arr = pkt.volume  # numpy array shaped (roiZ, roiY, roiX, C)

        # Ensure contiguous memory for safe/fast from_numpy
        arr_c = np.ascontiguousarray(arr)
        t = torch.from_numpy(arr_c)

        # dtype handling
        if self.dtype is not None:
            if isinstance(self.dtype, str):
                if not hasattr(torch, self.dtype):
                    raise ValueError(f"Unknown torch dtype string: {self.dtype!r}")
                t = t.to(getattr(torch, self.dtype))
            else:
                t = t.to(self.dtype)

        # device handling
        if self.device is not None:
            t = t.to(self.device)

        meta = {
            "time": pkt.time,
            "mode": pkt.mode,
            "shape_zyxc": pkt.shape_zyxc,
            "tiles_total": pkt.tiles_total,
            "tiles_included": pkt.tiles_included,
            "bytes_read": pkt.bytes_read,
            "decode_ms": pkt.decode_ms,
            "channels": pkt.channels,
            "tile_size": pkt.tile_size,
        }

        return TorchObservation(tensor=t, meta=meta)
