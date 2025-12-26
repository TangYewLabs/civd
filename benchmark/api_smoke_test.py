import numpy as np
from civd.core import World

def main():
    w = World.open(".")

    roi = w.roi_from_center_radius(zyx_center=(128,128,160), radius_vox=40, time="t001")
    sub_full, st_full = w.load_roi_tiles(time="t001", roi=roi, mode="full")
    sub_delta, st_delta = w.load_roi_tiles(time="t001", roi=roi, mode="delta")

    print("CIVD Core API Smoke Test")
    print("-----------------------")
    print("ROI:", roi)
    print("")
    print("t001 full tiles:", st_full.tiles_total, "decode_ms:", f"{st_full.decode_ms:.2f}", "bytes_read:", st_full.bytes_read_compressed)
    print("t001 delta tiles:", st_delta.tiles_total, "decode_ms:", f"{st_delta.decode_ms:.2f}", "bytes_read:", st_delta.bytes_read_compressed)

    # Build a base ROI buffer and replay delta tiles into it (synthetic base = zeros)
    Zr = roi.z1 - roi.z0
    Yr = roi.y1 - roi.y0
    Xr = roi.x1 - roi.x0
    C = sub_full.shape_zyxc[3]
    base = np.zeros((Zr, Yr, Xr, C), dtype=np.float32)

    out = World.replay(base, submap_tiles=sub_delta.tiles, tile_bounds_zyx=sub_delta.tile_bounds_zyx, roi=roi)
    print("Replayed delta into base ROI. min/max:", float(out.min()), float(out.max()))

if __name__ == "__main__":
    main()
