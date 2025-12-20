
# CIVD — Corpus Informaticus Volumetric Data

**CIVD** is a 3D-native, spatial–temporal data substrate designed for robotics,
simulation, and digital twin systems.

Unlike conventional file formats that merely *store* 3D assets, CIVD is built to
**operate in 3D space**:
- Spatially addressable
- ROI-first
- Tile-streamable
- Temporal-delta aware
- Compute-efficient

This repository contains a **reference implementation** with measurable,
reproducible benchmarks demonstrating how update cost scales with *change*, not
world size.

---

## Core Concepts

### Volumetric Address Space
All data lives in a true 3D voxel grid `(Z, Y, X, Channels)`.
Every read is spatially scoped — there is no “load the entire file” assumption.

### Tiles
The volume is partitioned into fixed-size **tiles** (e.g. `32×32×32` voxels).

Each tile is:
- Independently compressed
- Independently decodable
- Individually addressable

### ROI (Region of Interest)
An ROI defines a sub-volume query:
> “Load only this region of the world.”

CIVD resolves an ROI into the **minimal set of tiles** required to satisfy it.

---

## Phase C — ROI Tile Streaming

**Goal:** Avoid loading the full volume when only a region is needed.

### Benchmark
- Full volume size: ~134 MB
- ROI (~12.5% of volume):
  - Tiles decoded: 64
  - Memory used: ~16.8 MB
  - Decode time: ~32 ms

**Result:** ROI queries decode only the tiles intersecting the requested region.

---

## Phase D — Temporal Tile Packs

**Goal:** Avoid storing unchanged data across time.

CIVD introduces **temporal packs**:
- Unchanged tiles are referenced
- Changed tiles are stored once

### Result
- Initial frame (`t000`): 512 tiles stored
- Updated frame (`t001`): **8 tiles stored**
- **504 tiles reused** via references

**Result:** Storage scales with *change*, not with time.

---

## Phase D+ — ROI Delta-Only Decode

**Goal:** Avoid decoding unchanged tiles inside an ROI.

### Benchmark
- ROI tiles at `t001`: 64
- Changed tiles inside ROI: **8**
- Unchanged tiles reused by reference: 56

**Result:**
- ~87.5% fewer tiles decoded
- Dramatically reduced IO and decode time

---

## Phase E — Submap Export & Replay (SLAM-Style)

**Goal:** Emit robotics-native submap payloads suitable for SLAM and world-model
updates.

### Export Results (ROI near change region)

| Mode | Tiles | Decode Time | Export Size |
|-----|------|-------------|-------------|
| `t001` full ROI | 64 | ~31 ms | ~7.7 MB |
| **`t001` delta ROI** | **8** | **~5.4 ms** | **~1.0 MB** |

Each export includes:
- ROI bounds
- Tile bounds
- Tile payloads
- Timestamp and mode (`full` or `delta`)

### Replay
Exported submaps can be replayed to reconstruct the ROI deterministically,
verifying correctness and suitability for downstream robotics pipelines.

---

## Reproduce (Phase E)

From a fresh Python virtual environment:

```powershell
pip install -r requirements.txt
python scripts/repro_phase_e.py
```

Artifacts produced:
- `results/logs/*.json` — benchmark measurements
- `results/plots/*.png` — performance plots
- `exports/*.npz` — submap payloads

The reproduce script regenerates all Phase C–E results end-to-end.

---

## Repository Structure

```
civd/
benchmark/
scripts/
data/        # generated (ignored)
results/     # generated (ignored)
exports/     # generated (ignored)
```

---

## Status

- Phase C: ROI streaming ✅
- Phase D: Temporal tile packs ✅
- Phase D+: ROI delta-only decode ✅
- Phase E: Submap export & replay ✅

---

## What CIVD Enables

- ROI-first world memory for robotics
- Bandwidth-efficient SLAM updates
- Change-aware digital twin streaming
- Deterministic submap replay
- A stable foundation for future ROS2 or USD-style integrations

---

## License

Open research prototype.
Intended for experimentation, extension, and discussion.
