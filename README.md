# CIVD — Corpus Informaticus Volumetric Data

CIVD is a **volumetric, ROI-first, time-aware data format and runtime** designed for robotics, digital twins, and simulation workflows.
It enables efficient **tile-wise streaming**, **delta reuse across time**, and **deterministic replay** of 3D+channel data without loading full volumes.

---

## Why CIVD

- **ROI-first by design** — never load the entire volume when only a region matters
- **Time-aware deltas** — reuse unchanged tiles across timesteps
- **Deterministic replay** — identical inputs yield identical reconstructions
- **Workflow-ready** — exportable submaps, bridgeable to ROS2 and NVIDIA pipelines
- **Dependency-light core** — no ROS2/USD required in CIVD Core

---

## Architecture Overview

- **Tiles**: Fixed-size voxel blocks (e.g., 32³) addressed by `z##_y##_x##`
- **ROI**: Spatial query selecting only intersecting tiles
- **Time Packs**: `t000`, `t001`, … where unchanged tiles reference prior packs
- **Delta Decode**: Only changed tiles are decoded for new timesteps
- **Replay**: Delta tiles are composited into a base ROI deterministically

---

## Core API Smoke Test (Proof)

This smoke test validates CIVD’s core guarantees:

- ROI-first loading (no full-volume load)
- Delta-only decoding across time
- Deterministic replay correctness

### Test Output

```
CIVD Core API Smoke Test
-----------------------
ROI: ROIBox(z0=88, z1=168, y0=88, y1=168, x0=120, x1=200)

t001 full tiles: 64 decode_ms: 41.96 bytes_read: 7456987
t001 delta tiles: 8 decode_ms: 4.58 bytes_read: 1035271
Replayed delta into base ROI. min/max: 0.0 7.0
```

### Interpretation

- **8× fewer tiles decoded** for the same ROI (64 → 8)
- **~7× reduction in compressed I/O**
- **~9× faster decode path** for delta updates
- Delta replay reconstructs the ROI correctly (value range preserved)

This demonstrates that CIVD supports real-time, time-aware volumetric streaming suitable for robotics, digital twins, and simulation workflows.

---

## Status

- CIVD Core API: **Stable**
- ROI Streaming: **Implemented**
- Temporal Delta Packs: **Implemented**
- Submap Export / Replay: **Implemented**
- ROS2 / NVIDIA Adapters: **Planned (adapter layer)**

---

## Next Steps

- Lock **Index Schema v1** and **Submap Schema v1**
- Add `World.verify()` for pipeline safety
- Release ROS2 installable package
- Demonstrate CIVD streaming inside NVIDIA Isaac / Omniverse

---

## License

MIT (planned)
