import subprocess
import sys

def run(cmd):
    print("\n>>>", " ".join(cmd))
    subprocess.check_call(cmd)

def main():
    py = sys.executable

    # 0) generate synthetic volume
    run([py, "data/make_volume.py"])

    # 1) build tile pack (Phase C)
    run([py, "civd/tiler.py"])
    run([py, "-m", "benchmark.verify_tile_read"])

    # 2) ROI benchmark (Phase C)
    run([py, "-m", "benchmark.roi_load"])

    # 3) build timepacks (Phase D)
    run([py, "-m", "civd.temporal_tiler"])
    run([py, "-m", "civd.time_loader"])
    run([py, "-m", "benchmark.roi_time"])

    # 4) delta-only ROI plots (Phase D+)
    run([py, "-m", "benchmark.plot_roi_delta"])

    # 5) timepack plot (if present)
    try:
        run([py, "-m", "benchmark.plot_timepack"])
    except Exception:
        print("plot_timepack not found; skipping.")

    # 6) stream plots (if present)
    try:
        run([py, "-m", "benchmark.plot_stream"])
    except Exception:
        print("plot_stream not found; skipping.")

    print("\nDONE: Phase E reproducibility run complete.")

if __name__ == "__main__":
    main()
