# CIVD — Corpus Informaticus Volumetric Data

**CIVD** is a volumetric, ROI-first data container designed for robotics, digital twins, and advanced R&D workflows.

CIVD treats data as a **queryable 3D/4D volume**, not a file you load wholesale.

---

## Why CIVD Exists

Traditional file formats assume:
- Sequential loading
- Whole-file access
- Weak spatial or temporal locality

CIVD is designed around **how robots, simulators, and perception systems actually work**:

- Query *regions*, not files
- Decode *only what changed*
- Treat time as a first-class dimension

---

## Core Concepts

### 1. Data Is a Volume You Query

CIVD stores data in tiled volumetric space:

- Z / Y / X spatial axes
- Optional channel axis (C)
- Optional time axis (T)

You never load “the file” — you ask for a **Region of Interest (ROI)**.

```python
roi = ROIBox(z0=88, z1=168, y0=88, y1=168, x0=120, x1=200)
submap, stats = world.load_roi_tiles(time="t001", roi=roi, mode="full")
```

---

### 2. ROI-First by Design

All operations begin with ROI:
- Decode
- Stream
- Delta-update
- Replay

This aligns directly with:
- Robot perception cones
- Camera frustums
- Simulation focus regions
- Active learning loops

---

### 3. Temporal Delta Encoding

CIVD supports **delta tiles** across time:

- Only changed tiles are stored
- Unchanged tiles reference prior time indices
- Deltas can be replayed into a base ROI

```python
sub_delta, stats = world.load_roi_tiles(time="t001", roi=roi, mode="delta")
replayed = world.replay_delta(base=sub_full, delta=sub_delta)
```

---

## Measured Proof (Smoke Test)

```bash
python -m benchmark.api_smoke_test
```

Example output:

```
CIVD Core API Smoke Test
-----------------------
ROI: ROIBox(z0=88, z1=168, y0=88, y1=168, x0=120, x1=200)

t001 full tiles: 64 decode_ms: 36.20 bytes_read: 7456987
t001 delta tiles: 8 decode_ms: 4.76 bytes_read: 1035271
Replayed delta into base ROI. min/max: 0.0 7.0
```

---

## Installation (Local / Dev)

```bash
git clone https://github.com/your-org/civd.git
cd civd_phase_c
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Verify:

```bash
python -c "from civd import World, ROIBox; print('OK')"
```

---

## Exporting Submaps

```bash
python -m civd.export_submap
```

Outputs:
- `.npz` compressed ROI volume
- `.json` manifest (civd.submap.v1)

Supports:
- `mode="full"`
- `mode="delta"`

---

## Target Use Cases

CIVD is **not a general-purpose file format**.

It is intentionally designed for:

- Robotics (ROS2, SLAM, perception)
- Digital twins (Isaac Sim, Omniverse-style workflows)
- Simulation playback
- R&D experimentation
- Temporal spatial analytics

---

## Why This Is Different

CIVD enables **new workflows**:

| Traditional | CIVD |
|------------|------|
| Load file | Query space |
| Recompute | Replay deltas |
| Full decode | ROI decode |
| Time as metadata | Time as structure |

---

## Roadmap (Locked Direction)

- ROS2 bridge (optional, installable)
- Streaming ROI updates
- GPU-backed decode paths
- Isaac Sim integration examples
- Schema stabilization (v1.x)

---

## Status

CIVD is a **research-grade, working system**.

It is intentionally scoped for:
- Serious experimentation
- Advanced engineering workflows
- Open exploration of volumetric-first data systems

---

## License

MIT (planned for v1 open-source release)
