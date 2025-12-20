from __future__ import annotations

import argparse
import json
import os

from civd.schema import verify_index_v1


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify CIVD index schema v1")
    ap.add_argument("--time", required=True, help="t000 / t001 / ...")
    ap.add_argument("--root", default=".", help="repo root")
    args = ap.parse_args()

    path = os.path.join(args.root, "data", "civd_time", args.time, "index.json")
    if not os.path.exists(path):
        raise SystemExit(f"Index not found: {path}")

    idx = json.load(open(path, "r", encoding="utf-8"))
    verify_index_v1(idx)
    print(f"OK: {path} conforms to civd.index.v1")


if __name__ == "__main__":
    main()
