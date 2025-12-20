import numpy as np


def reconstruct_roi_from_tiles(tiles, bounds_zyx, roi_zyx, channels: int):
    z0, z1, y0, y1, x0, x1 = roi_zyx
    out = np.zeros((z1 - z0, y1 - y0, x1 - x0, channels), dtype=np.float32)

    for tile, b in zip(tiles, bounds_zyx):
        tz0, tz1, ty0, ty1, tx0, tx1 = b

        cz0 = max(tz0, z0); cz1 = min(tz1, z1)
        cy0 = max(ty0, y0); cy1 = min(ty1, y1)
        cx0 = max(tx0, x0); cx1 = min(tx1, x1)

        if cz0 >= cz1 or cy0 >= cy1 or cx0 >= cx1:
            continue

        sz0 = cz0 - tz0; sz1 = sz0 + (cz1 - cz0)
        sy0 = cy0 - ty0; sy1 = sy0 + (cy1 - cy0)
        sx0 = cx0 - tx0; sx1 = sx0 + (cx1 - cx0)

        dz0 = cz0 - z0; dz1 = dz0 + (cz1 - cz0)
        dy0 = cy0 - y0; dy1 = dy0 + (cy1 - cy0)
        dx0 = cx0 - x0; dx1 = dx0 + (cx1 - cx0)

        out[dz0:dz1, dy0:dy1, dx0:dx1, :] = tile[sz0:sz1, sy0:sy1, sx0:sx1, :]

    return out


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m benchmark.replay_submap exports/<submap>.npz")
        return

    path = sys.argv[1]
    d = np.load(path, allow_pickle=True)

    tiles = d["tiles"]
    bounds = d["tile_bounds_zyx"]
    roi = d["roi"]
    mode = str(d["mode"])
    ts = str(d["timestamp"])

    channels = tiles.shape[-1] if tiles.ndim == 5 else 2
    out = reconstruct_roi_from_tiles(tiles, bounds, roi, channels)

    print("Replayed submap:")
    print("  path:", path)
    print("  timestamp:", ts, "mode:", mode)
    print("  tiles:", tiles.shape[0])
    print("  roi shape:", out.shape)
    print("  min/max:", float(out.min()), float(out.max()))


if __name__ == "__main__":
    main()
