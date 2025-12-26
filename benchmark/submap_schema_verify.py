from __future__ import annotations

import argparse
import json
import os

from civd.submap_schema import verify_submap_v1


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify CIVD submap manifest schema v1")
    ap.add_argument("--manifest", required=True, help="Path to exports/*.json manifest")
    args = ap.parse_args()

    path = args.manifest
    if not os.path.exists(path):
        raise SystemExit(f"Manifest not found: {path}")

    m = json.load(open(path, "r", encoding="utf-8"))
    verify_submap_v1(m)
    print(f"OK: {path} conforms to civd.submap.v1")


if __name__ == "__main__":
    main()
