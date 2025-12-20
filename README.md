# CIVD — Corpus Informaticus Volumetric Data

CIVD is a **3D-native data format** where *space is the primary index*, enabling ROI-first access, tile-wise compression, streaming, and temporal reuse of volumetric intelligence for robotics and digital twins.

---

## What CIVD Is (and Is Not)

**CIVD is NOT:**
- A container for meshes or 3D assets
- A scene graph or geometry format
- A point cloud wrapper

**CIVD IS:**
- A volumetric data substrate where data is organized intrinsically in 3D space
- Spatially indexed at rest (not reconstructed after load)
- Designed for ROI-first access and streaming
- Time-aware through changed-tile-only temporal packs
- Aligned with SLAM submaps and USD payload streaming, but tool-agnostic

---

## Phase C — Tile-Wise Compression + ROI Streaming

Phase C demonstrates that a **single CIVD file** can be reused over time to load *different regions of interest (ROIs)* without loading the entire volume.

> *You don’t load the whole city just to visit one block.*

### Test Dataset
- Volume: `256 × 256 × 256 × 2` (float32)
- Channels: density + semantic labels
- Tile size: `32 × 32 × 32`
- Total tiles: `512 (8 × 8 × 8)`

### ROI Benchmark Results

**Full volume load**
- Size: **134.22 MB**
- Load time: **45.37 ms**
- Memory delta: **~134 MB**

**ROI load (64 tiles)**
- Compressed bytes read: **7.47 MB**
- Decoded bytes produced: **16.78 MB**
- ROI = **12.5%** of full volume
- Decode time: **32.44 ms**
- Memory delta: **~16.83 MB**

**Result:** CIVD decodes only the spatial region required, with predictable memory and reduced IO.

### Dynamic ROI Streaming

CIVD was tested with a moving ROI to simulate robot motion or camera movement.

Observed behavior:
- Cold start loads required tiles once
- Subsequent steps are **cache-hit dominated**
- Disk reads occur only when new tiles enter the ROI
- After warming, incremental steps approach **near-zero additional IO**

![Cache hits vs misses](results/plots/stream_hits_misses.png)
![Compressed MB read per step](results/plots/stream_mb_read.png)
![Decode time per step](results/plots/stream_decode_ms.png)

---

## Phase D — Temporal Packs (Changed-Tile-Only Updates)

Phase D extends CIVD with **timepacks**: tile-pack versions over time where unchanged tiles are **reused by reference** and only changed tiles are stored for the new timestamp.

> *You don’t rewrite the whole city when one block changes.*

### Global Update Behavior
- `t000` (initial write): **512 changed**, 0 reused
- `t001` (localized change): **8 changed**, **504 reused**
- Only **1.56%** of the world required new storage

### ROI Delta Behavior
For an ROI of 64 tiles near the changed region:
- `t000`: 64 tiles decoded
- `t001`: 64 tiles decoded, but only **8** required new storage
- 56 tiles were resolved by reference back to `t000`

![Changed vs reused tiles](results/plots/timepack_changed_vs_reused.png)

**Takeaway:** CIVD acts as a **spatial–temporal memory substrate**, not just a storage format.

---

## Why This Matters

CIVD makes a different assumption than traditional formats:

> **Space (and time) are the index, not the payload.**

This enables:
- ROI-first perception
- Submap-native storage
- Bounded IO as worlds evolve
- Predictable memory usage
- Efficient replay and change inspection
- Reuse of the same world file across time and viewpoints

---

## Status

This repository is a **research prototype** demonstrating CIVD Phase C and Phase D.

Planned future work:
- ROI delta-only decode (decode only changed tiles)
- Tile delta compression
- GPU-native decode paths
- Integration with simulation and robotics frameworks

---

## 60-Second Demo

```powershell
# Phase C
python data/make_volume.py
python civd/tiler.py
python -m benchmark.roi_load

# Phase D
python data/make_volume_t1.py
python -m civd.temporal_tiler
python -m benchmark.roi_time

# Plots
python -m benchmark.stream_load
python -m benchmark.plot_stream
python -m benchmark.plot_timepack
```
