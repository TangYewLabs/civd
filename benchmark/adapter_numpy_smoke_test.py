from civd import World, ROIBox
from civd.source import ObservationRequest
from civd.adapters import NumpyAdapter

def main():
    w = World.open(".")
    src = w.as_observation_source()
    ad = NumpyAdapter(src)

    roi = ROIBox(88, 168, 88, 168, 120, 200)

    req_full = ObservationRequest(time_name="t001", roi=roi, mode="full")
    obs_full = ad.get(req_full)
    print("numpy FULL", obs_full.array.shape, obs_full.meta["tiles_included"], "{:.2f}ms".format(obs_full.meta["decode_ms"]))

    req_delta = ObservationRequest(time_name="t001", roi=roi, mode="delta")
    obs_delta = ad.get(req_delta)
    print("numpy DELTA", obs_delta.array.shape, obs_delta.meta["tiles_included"], "{:.2f}ms".format(obs_delta.meta["decode_ms"]))

if __name__ == "__main__":
    main()
