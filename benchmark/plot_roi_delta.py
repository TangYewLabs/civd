import matplotlib.pyplot as plt

from civd.roi import roi_from_center_radius, roi_tiles
from civd.roi_delta import roi_delta_tiles
from civd.time_loader import load_index


def main():
    t0_path = "data/civd_time/t000/index.json"
    t1_path = "data/civd_time/t001/index.json"

    idx0 = load_index(t0_path)
    idx1 = load_index(t1_path)

    Z, Y, X, _ = idx0["volume"]["shape_zyxc"]

    roi = roi_from_center_radius(
    (128, 128, 160),
    40,
    (Z, Y, X),
    )

    tiles_full = roi_tiles(idx1, roi)
    tiles_delta = roi_delta_tiles(idx1, roi)

    plt.figure()
    plt.title("CIVD Phase D+ — ROI Update Decode: Full vs Delta-Only")
    plt.bar(
        ["t001 full ROI", "t001 delta-only"],
        [len(tiles_full), len(tiles_delta)],
    )
    plt.ylabel("Tiles decoded")
    plt.tight_layout()
    plt.savefig("results/plots/roi_delta_tiles.png", dpi=160)
    plt.show()

    print("Saved: results/plots/roi_delta_tiles.png")
    print("t001 full ROI tiles:", len(tiles_full))
    print("t001 delta-only tiles:", len(tiles_delta))


if __name__ == "__main__":
    main()
