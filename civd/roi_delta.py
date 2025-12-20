from typing import Dict, List

from civd.roi import roi_tiles, ROIBox


def roi_delta_tiles(index: Dict, roi: ROIBox) -> List[Dict]:
    """
    Returns only the tiles inside ROI that are *new at this timestamp*.
    In Phase D timepacks, unchanged tiles have a 'ref' field.
    Changed tiles are stored locally and have no 'ref'.
    """
    tiles = roi_tiles(index, roi)
    return [t for t in tiles if "ref" not in t]
