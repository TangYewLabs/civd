from civd import World, ROIBox
from civd.bridge import volume_to_voxelgrid_npz


def main() -> None:
    print("CIVD Bridge VoxelGrid Smoke Test")
    print("-------------------------------")

    w = World.open(".")
    roi = ROIBox(88, 168, 88, 168, 120, 200)

    pkt = w.query(time_name="t001", roi=roi, mode="delta")
    out_path = volume_to_voxelgrid_npz(pkt, "exports/voxelgrid_t001_delta_roi.npz")

    print("wrote:", out_path)
    print("shape:", pkt.shape_zyxc, "tiles_included:", pkt.tiles_included, "decode_ms:", f"{pkt.decode_ms:.2f}ms")


if __name__ == "__main__":
    main()
