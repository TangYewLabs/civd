import os
from civd.export_submap import export_submap


def fsize(path: str) -> int:
    return os.path.getsize(path) if os.path.exists(path) else 0


def main():
    center = (128, 128, 160)
    r = 40
    t1 = "data/civd_time/t001/index.json"

    m_full = export_submap(t1, center, r, mode="full")
    m_delta = export_submap(t1, center, r, mode="delta")

    full_npz = m_full["npz_path"]
    delta_npz = m_delta["npz_path"]

    print("CIVD Phase E — Submap Export Benchmark")
    print("-------------------------------------")
    print("t001 full ROI submap")
    print("  tiles:", m_full["tile_count"])
    print("  decode_ms:", f'{m_full["decode_ms"]:.2f}')
    print("  npz bytes:", fsize(full_npz))
    print("")
    print("t001 delta-only submap")
    print("  tiles:", m_delta["tile_count"])
    print("  decode_ms:", f'{m_delta["decode_ms"]:.2f}')
    print("  npz bytes:", fsize(delta_npz))
    print("")
    if fsize(full_npz) > 0:
        ratio = fsize(delta_npz) / fsize(full_npz)
        print(f"Export size ratio (delta/full): {ratio:.3f}  ({(1-ratio)*100:.2f}% smaller)")


if __name__ == "__main__":
    main()
