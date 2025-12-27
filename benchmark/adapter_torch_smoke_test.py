from civd import World, ROIBox
from civd.source import ObservationRequest
from civd.adapters import TorchAdapter


def main():
    print("CIVD Torch Adapter Smoke Test")
    print("----------------------------")

    w = World.open(".")
    src = w.as_observation_source()
    ad = TorchAdapter(src, channels_first=False, copy=True)

    roi = ROIBox(88, 168, 88, 168, 120, 200)

    req_full = ObservationRequest(time_name="t001", roi=roi, mode="full")
    obs_full = ad.get(req_full)
    print(
        "torch FULL ",
        tuple(obs_full.tensor.shape),
        obs_full.meta["tiles_included"],
        f'{obs_full.meta["decode_ms"]:.2f}ms',
        obs_full.meta["bytes_read"],
    )

    req_delta = ObservationRequest(time_name="t001", roi=roi, mode="delta")
    obs_delta = ad.get(req_delta)
    print(
        "torch DELTA",
        tuple(obs_delta.tensor.shape),
        obs_delta.meta["tiles_included"],
        f'{obs_delta.meta["decode_ms"]:.2f}ms',
        obs_delta.meta["bytes_read"],
    )


if __name__ == "__main__":
    main()
