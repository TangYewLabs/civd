# CIVD — Corpus Informaticus Volumetric Data

CIVD is a **volumetric data container** that treats data as **queryable 3D space over time**, not a flat file.

Instead of loading entire datasets, CIVD enables systems to:
- Query **regions of interest (ROI)** in 3D space
- Replay **delta-only changes** across time
- Treat data as **spatial state**, suitable for robotics, simulation, AI, and R&D workflows

CIVD is intentionally **not** a generic file format. It is a **spatial state container**.

---

## Core Idea

> **CIVD treats data as a volume you query, not a file you load.**

You don’t ask:
- “Open this file”

You ask:
- “Give me *this region*, at *this time*, with *only what changed*.”

This enables workflows that traditional file formats cannot support.

---

## What CIVD Is (and Is Not)

### CIVD **IS**
- A **3D + time data container**
- A **spatial state representation**
- ROI-first (partial decode by default)
- Delta-aware across time
- Schema-versioned and deterministic
- Designed for **R&D, robotics, simulation, AI, digital twins**

### CIVD **IS NOT**
- A replacement for CSV / Parquet / JSON
- A generic storage format
- A consumer file format
- A database

This focus is deliberate.

---

## Why CIVD Exists

Modern systems increasingly operate on:
- Spatial data
- Time-indexed state
- Large volumes where **full reloads are wasteful**

Traditional files force you to load everything. CIVD lets you touch **only what matters**.

---

## Key Capabilities

### 1. Spatial Queries (ROI)
- Extract only the region you need
- Decode partial volumes
- Skip irrelevant data entirely

### 2. Temporal Deltas
- Tiles can reference prior time steps
- Only changed regions are decoded
- Efficient replay and comparison

### 3. Schema-Versioned Core
- `civd.index.v1` — volume + tiles + time
- `civd.submap.v1` — exported ROI manifests
- Deterministic validation

---

## Installation

```bash
git clone https://github.com/TangYewLabs/civd.git
cd civd
python -m venv .venv
```

### Activate Virtual Environment

**Windows (PowerShell)**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -U pip
pip install numpy zstandard
```

---

## Quickstart — Export Spatial Submaps

```bash
python -m civd.export_submap
```

This performs:
- Full ROI export at `t000`
- Full ROI export at `t001`
- Delta-only ROI export at `t001`

Outputs:
- `exports/*.npz` — ROI volume data
- `exports/*.json` — manifest (`civd.submap.v1`)

---

## Core API Smoke Test (Proof)

Example real output:

```
Exported: exports/submap_t000_full_z128_y128_x160_r40.npz
  tiles: 64 decode_ms: 31.36 bytes: 2031447

Exported: exports/submap_t001_full_z128_y128_x160_r40.npz
  tiles: 64 decode_ms: 67.64 bytes: 2046525

Exported: exports/submap_t001_delta_z128_y128_x160_r40.npz
  tiles: 8 decode_ms: 5.71 bytes: 1068557
```

This demonstrates:
- ROI querying
- Delta-only decoding
- Tile reuse across time
- Performance scaling with **change**, not dataset size

---

## Schemas

### `civd.index.v1`
Defines:
- Volume shape (ZYXC)
- Tile grid
- Time index
- Tile metadata and references

### `civd.submap.v1`
Defines:
- ROI bounds
- Tiles included vs skipped
- Decode metrics
- Provenance and source index

---

## Validate Schemas

```bash
python -m benchmark.schema_verify --time t000
python -m benchmark.schema_verify --time t001
```

---

## Upgrade Legacy Indices

```bash
python -m civd.upgrade_index --time t000
python -m civd.upgrade_index --time t001
```

---

## Where CIVD Is Useful

CIVD is specialized, not niche.

**Strong fit:**
- Robotics perception buffers
- Simulation state capture
- Digital twin snapshots
- Spatial AI datasets
- Research and experimental systems

Especially valuable for:
- NVIDIA Isaac Sim
- Omniverse-based pipelines
- Robotics R&D

---

## Is CIVD Still Groundbreaking?

Yes. Files do not behave like worlds.

CIVD enables:
- Querying space instead of loading files
- Treating time as first-class
- Replaying physical state efficiently

It is a **capability primitive**, not a convenience format.

---

## Design Philosophy

- Correctness over convenience
- Explicit schemas over inference
- Partial decode over full load
- R&D velocity over mass adoption

---

## Status

- Core index schema: **stable**
- Submap export: **working**
- Delta replay: **validated**
- Tooling: **active development**

---

## License

MIT

