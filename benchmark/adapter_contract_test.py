"""
CIVD Adapter Contract Test (no pytest)

Run:
  python -m benchmark.adapter_contract_test
"""
from __future__ import annotations

from civd import World, ROIBox
from civd.source import ObservationRequest, VolumePacket
from civd.adapters import NumpyAdapter

REQUIRED_META_KEYS = {
    "time_name",
    "mode",
    "shape_zyxc",
    "tiles_included",
    "bytes_read",
    "decode_ms",
}

def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)

def _meta_check(meta, label):
    missing = [k for k in REQUIRED_META_KEYS if k not in meta]
    _assert(not missing, f"{label}: missing meta keys {missing}")

def main():
    print("CIVD Adapter Contract Test")
    print("--------------------------")

    w = World.open(".")
    src = w.as_observation_source()

    roi = ROIBox(88, 168, 88, 168, 120, 200)
    req_full = ObservationRequest("t001", roi, mode="full")
    req_delta = ObservationRequest("t001", roi, mode="delta")

    pkt = src.observe(req_full)
    _assert(isinstance(pkt, VolumePacket), "observe must return VolumePacket")

    nad = NumpyAdapter(src)
    obs = nad.get(req_delta)
    _meta_check(obs.meta, "numpy")

    print("PASS")

if __name__ == "__main__":
    main()
