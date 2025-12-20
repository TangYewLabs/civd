from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from civd.roi import roi_tiles, ROIBox
from civd.roi_delta import roi_delta_tiles
from civd.time_loader import load_index, decode_tile_from_entry


@dataclass
class StreamStats:
    hits: int = 0
    misses: int = 0
    bytes_read: int = 0
    decode_ms: float = 0.0


class LRUCache:
    def __init__(self, max_tiles: int = 128):
        self.max_tiles = max_tiles
        self._d: "OrderedDict[str, np.ndarray]" = OrderedDict()

    def get(self, key: str):
        if key in self._d:
            self._d.move_to_end(key)
            return self._d[key]
        return None

    def put(self, key: str, value: np.ndarray):
        self._d[key] = value
        self._d.move_to_end(key)
        while len(self._d) > self.max_tiles:
            self._d.popitem(last=False)

    def __len__(self):
        return len(self._d)


class USDLikeStream:
    """
    A USD-inspired streaming surface for CIVD:
      - load_region(roi): load full ROI tiles
      - apply_delta(roi): load only changed tiles inside ROI (refs are cache hits)
      - unload_region(): drop tiles from cache by ROI
    """

    def __init__(self, index_path: str, cache_tiles: int = 128):
        self.idx = load_index(index_path)
        self.pack_path = self.idx["pack"]["path"]
        self.cache = LRUCache(max_tiles=cache_tiles)

    def _io_estimate(self, entry: Dict) -> int:
        if "ref" in entry:
            return int(entry["ref"]["length"])
        return int(entry["length"])

    def load_region(self, roi: ROIBox) -> Tuple[np.ndarray, StreamStats]:
        tiles = roi_tiles(self.idx, roi)
        return self._load_tiles(tiles)

    def apply_delta(self, roi: ROIBox) -> Tuple[np.ndarray, StreamStats]:
        tiles = roi_delta_tiles(self.idx, roi)
        return self._load_tiles(tiles)

    def _load_tiles(self, tiles: List[Dict]) -> Tuple[np.ndarray, StreamStats]:
        import time
        stats = StreamStats()
        decoded = []

        t0 = time.perf_counter()
        for entry in tiles:
            tid = entry["tile_id"]
            cached = self.cache.get(tid)
            if cached is not None:
                stats.hits += 1
                decoded.append(cached)
                continue

            stats.misses += 1
            stats.bytes_read += self._io_estimate(entry)
            arr = decode_tile_from_entry(entry, self.pack_path)
            self.cache.put(tid, arr)
            decoded.append(arr)

        t1 = time.perf_counter()
        stats.decode_ms = (t1 - t0) * 1000.0

        if decoded:
            tiles_arr = np.stack(decoded, axis=0).astype(np.float32, copy=False)
        else:
            # no-op delta is valid
            C = self.idx["volume"]["shape_zyxc"][3]
            tiles_arr = np.zeros((0, 1, 1, 1, C), dtype=np.float32)

        return tiles_arr, stats

    def unload_region(self, roi: ROIBox) -> int:
        """
        Removes cached tiles that intersect this ROI.
        Returns number of removed tiles.
        """
        # simplest: remove all ROI tiles from cache
        tiles = roi_tiles(self.idx, roi)
        removed = 0
        for entry in tiles:
            tid = entry["tile_id"]
            if tid in self.cache._d:
                del self.cache._d[tid]
                removed += 1
        return removed
