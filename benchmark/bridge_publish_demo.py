import numpy as np

from civd.export_submap import export_submap
from bridge.msg import SubmapDeltaMsg
from bridge.pubsub import publish_to_dir, load_from_base
from benchmark.replay_submap import reconstruct_roi_from_tiles


def msg_from_export(export_json_path: str) -> SubmapDeltaMsg:
    import json
    with open(export_json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    npz_path = meta["npz_path"]

    d = np.load(npz_path, allow_pickle=True)

    tiles = d["tiles"]
    bounds = d["tile_bounds_zyx"]
    roi = tuple(d["roi"].tolist())

    return SubmapDeltaMsg(
        schema="civd.phase_f.submap_delta_msg.v1",
        timestamp=meta["timestamp"],
        mode=meta["mode"],
        roi_zyx=roi,
        tile_bounds_zyx=bounds,
        tiles=tiles,
        compressed_bytes_read_est=meta.get("compressed_bytes_read_est"),
        decode_ms=meta.get("decode_ms"),
    )


def main():
    # Ensure exports exist (creates or overwrites)
    export_submap("data/civd_time/t001/index.json", (128, 128, 160), 40, mode="delta", out_dir="exports")

    export_json = "exports/submap_t001_delta_z128_y128_x160_r40.json"
    msg = msg_from_export(export_json)

    base = publish_to_dir(msg, out_dir="bridge_out")
    print("Published base:", base)

    rx = load_from_base(base)

    # reconstruct ROI
    channels = rx.tiles.shape[-1] if rx.tiles.ndim == 5 else 2
    roi_arr = reconstruct_roi_from_tiles(rx.tiles, rx.tile_bounds_zyx, rx.roi_zyx, channels)

    print("Subscriber reconstructed ROI:")
    print("  tiles:", rx.tiles.shape[0])
    print("  roi shape:", roi_arr.shape)
    print("  min/max:", float(roi_arr.min()), float(roi_arr.max()))


if __name__ == "__main__":
    main()
