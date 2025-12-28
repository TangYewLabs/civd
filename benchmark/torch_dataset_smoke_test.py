from civd import World, ROIBox
from civd.source import ObservationRequest
from civd.adapters import TorchAdapter


def main() -> None:
    print("CIVD Torch Dataset Smoke Test")
    print("-----------------------------")

    w = World.open(".")
    src = w.as_observation_source()

    ad = TorchAdapter(src, device="cpu", channels_first=False, copy=True)

    roi = ROIBox(88, 168, 88, 168, 120, 200)
    times = ["t000", "t001"]

    for tname in times:
        req = ObservationRequest(time_name=tname, roi=roi, mode="delta")
        obs = ad.get(req)
        print(
            "time:", tname,
            "tensor:", tuple(obs.tensor.shape),
            "tiles:", obs.meta["tiles_included"],
            "{:.2f}ms".format(obs.meta["decode_ms"]),
        )


if __name__ == "__main__":
    main()
