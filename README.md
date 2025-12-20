
# CIVD — Corpus Informaticus Volumetric Data

**CIVD** is a 3D-native, spatial–temporal data substrate designed for robotics, simulation, and digital twin systems.

Unlike conventional file formats that merely *store* 3D data, CIVD is built to **operate in 3D space**:
- Spatially addressable
- ROI-first
- Tile-streamable
- Temporal-delta aware
- Compute-efficient

This repository contains a **reference implementation** with benchmarks demonstrating how update cost scales with *change*, not world size.

---

## Core Concepts

### 1. Volumetric Address Space
Data is stored in a 3D voxel grid (Z, Y, X) with per-voxel channels.  
Everything in CIVD is spatially indexed — there is no “load the whole file” assumption.

### 2. Tiles
The volume is partitioned into fixed-size **tiles** (e.g., 32×32×32 voxels).
Tiles are:
- Independently compressed
- Independently decodable
- Individually addressable

### 3. ROI (Region of Interest)
An ROI defines a sub-volume query:
> “Load only this region of the world.”

CIVD resolves an ROI into the **minimal set of tiles** required to satisfy it.

### 4. Temporal Packs
CIVD supports time-indexed volumes:
- Unchanged tiles are *referenced*
- Changed tiles are *stored once*
This enables efficient world updates.

---

## Phase C — ROI Tile Streaming

**Goal:** Avoid loading the full volume when only a region is needed.

### Benchmark
- Full volume: ~134 MB
- ROI (12.5% of volume):
  - Tiles decoded: 64
  - Memory used: ~16.8 MB
  - Decode time: ~32 ms

**Result:** ROI queries decode only the necessary tiles.

---

## Phase D — Temporal Tile Packs

**Goal:** Avoid storing unchanged data across time.

### Result
- Initial frame (`t000`): 512 tiles stored
- Updated frame (`t001`): **only 8 tiles stored**
- 504 tiles reused via references

**Result:** Storage scales with *change*, not time.

---

## Phase D+ — ROI Delta-Only Decode

**Goal:** Avoid decoding unchanged tiles during updates.

### Benchmark (ROI centered near change)
- Full ROI decode at `t001`: **64 tiles**
- Delta-only ROI decode at `t001`: **8 tiles**

**Reduction:**  
- 87.5% fewer tiles decoded  
- Significant IO and decode-time reduction

**Takeaway:** Update cost scales with *change*, not ROI size.

---

## Phase E — SLAM-Style Submap Export + Replay

**Goal:** Emit robotics-native submap payloads suitable for SLAM and world-model updates.

### Export Results (ROI near change region)

| Mode | Tiles | Decode Time | Compressed Read | Export Size |
|---|---|---|---|---|
| Full ROI (`t001`) | 64 | ~31 ms | ~7.46 MB | ~7.7 MB |
| **Delta-only ROI (`t001`)** | **8** | **~5.4 ms** | **~1.03 MB** | **~1.02 MB** |

**Result:** World updates can be streamed as compact submap deltas.

---

## Repository Structure

```
civd/
benchmark/
data/        # generated (ignored)
results/     # generated (ignored)
exports/     # generated (ignored)
```

---

## Status

- Phase C: ROI streaming ✅
- Phase D: Temporal tile packs ✅
- Phase D+: Delta-only ROI decode ✅
- Phase E: Submap export & replay ✅

---

## License

Open research prototype.  
Intended for experimentation, extension, and discussion.
