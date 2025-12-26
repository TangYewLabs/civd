# CIVD — Corpus Informaticus Volumetric Data

CIVD is a **volumetric data container** that treats data as a **queryable 3D space**, not a file you load wholesale.

Instead of loading entire datasets, CIVD lets systems ask:
> “Give me this region, at this time, optionally only what changed.”

It is designed for **robotics, simulation, digital twins, and machine learning systems** where bandwidth, memory, and compute efficiency matter.

---

## Core Idea (Explain Like I’m Five)

Imagine your data is a **giant Rubik’s Cube**.

- Each small cube holds information  
- You don’t pick up the whole cube  
- You only grab the cubes you need  
- If nothing changed, you grab nothing  

That’s CIVD.

---

## Why CIVD Exists

Traditional data pipelines force systems to:
- Load entire files
- Decode everything
- Move massive tensors repeatedly

CIVD lets systems:
- Query space instead of files
- Request only Regions of Interest (ROI)
- Pull **delta updates** instead of full volumes
- Reduce GPU, CPU, disk, and network usage

---

## What CIVD Does

CIVD provides:

- 3D spatial indexing
- Tile-based volumetric storage
- ROI-based queries
- Delta extraction across time steps
- Adapter-ready outputs for ML and robotics frameworks

---

## Key Concepts

### Volumetric Space
Data is stored as a **Z–Y–X–C volume**, not rows or blobs.

### ROI Queries
```python
ROIBox(z0, z1, y0, y1, x0, x1)
```

Only that region is decoded.

### Delta Mode
```python
mode="delta"
```

Only tiles that changed since the base frame are read.

---

## Example

```python
from civd import World, ROIBox

w = World.open(".")

roi = ROIBox(88, 168, 88, 168, 120, 200)

pkt_full = w.query(time_name="t001", roi=roi, mode="full")
pkt_delta = w.query(time_name="t001", roi=roi, mode="delta")

print(pkt_full.tiles_included, pkt_full.bytes_read)
print(pkt_delta.tiles_included, pkt_delta.bytes_read)
```

Example output:
```
FULL  64 tiles   ~7.4 MB
DELTA  8 tiles   ~1.0 MB
```

---

## Why This Matters

### Robotics & Simulation
- Faster training loops
- Reduced GPU memory pressure
- Lower I/O overhead
- Enables large worlds and long time horizons

### Digital Twins
- Stream only what changes
- Persistent spatial memory
- Efficient replay and analysis

CIVD improves **the system itself**, not the user workflow.

---

## Adapter Model (Phase C)

CIVD outputs are designed to feed:

- NumPy
- PyTorch
- ROS2
- Isaac Sim (via adapter)

CIVD does **not replace** these systems.  
It supplies them with **exactly the data they need, when they need it**.

---

## What CIVD Is Not

- Not a database
- Not a visualization tool
- Not a generic file format

CIVD is **infrastructure**.

---

## Project Status

- Phase C complete
- ROI queries implemented
- Delta extraction implemented
- Benchmarks validated
- Public API stabilized

Optional future work:
- Isaac Sim adapter
- PyTorch Observation adapter
- ROS2 streaming adapter

---

## License

MIT
