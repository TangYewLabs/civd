# Why CIVD

CIVD (Corpus Informaticus Volumetric Data) is an ROI-first volumetric data capsule with delta-aware streaming.

Instead of decoding entire volumetric worlds every step, CIVD allows downstream systems to request only the spatial region and data channels they need — and optionally only what changed.

---

## What problem CIVD solves

Modern robotics, simulation, and digital twin pipelines waste compute, memory bandwidth, and time by repeatedly decoding large volumes where most data is unchanged.

CIVD introduces three core ideas:

- **ROI-first access**: query only the spatial window required
- **Delta mode**: retrieve only tiles that changed between time steps
- **Stable adapter contract**: downstream tools integrate via adapters, not CIVD internals

---

## Primary use cases

### 1. Robot learning (PyTorch training loops)
Training often focuses on localized interaction regions (grasping, contact, manipulation).

CIVD reduces:
- Decode cost per step
- Memory pressure
- Dataset I/O overhead

### 2. Simulation training (Isaac / physics environments)
High-frequency voxel, occupancy, or semantic fields change only locally.

CIVD enables:
- Faster environment stepping
- Efficient partial state pulls
- Scalable multi-agent simulation

### 3. Digital twin streaming
Industrial, facility, or city-scale digital twins rarely change globally.

CIVD supports:
- Localized updates
- Efficient change propagation
- Scalable live-state streaming

---

## Benchmarks (from this repository)

Same ROI queried in FULL vs DELTA mode:

- **Tiles decoded:** 64 → 8
- **Bytes read:** ~7.4 MB → ~1.0 MB
- **Decode time:** ~96 ms → ~6–7 ms

This demonstrates CIVD’s design goal:

> Decode less. Move less. Iterate faster.

---

## Concept: ROI tiles vs delta tiles

Legend:
- `.` = outside ROI
- `R` = inside ROI
- `D` = changed tile (delta payload)

### ROI selection
```
. . . . . . . .
. . . R R R . .
. . . R R R . .
. . . R R R . .
. . . . . . . .
```

### Delta inside ROI
```
. . . . . . . .
. . . D R D . .
. . . R R R . .
. . . D R R . .
. . . . . . . .
```

FULL mode decodes all ROI tiles.  
DELTA mode decodes only the tiles marked `D`.

---

## Integration model

CIVD enforces a stable contract boundary:

1. Open a world and obtain an observation source
2. Attach an adapter (NumPy, Torch, ROS, etc.)
3. Request data via `ObservationRequest`

Downstream systems never depend on CIVD internals.

This keeps integrations stable as CIVD evolves.
