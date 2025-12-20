import io
import json
import numpy as np

def ros2_available() -> bool:
    try:
        import rclpy  # noqa: F401
        from std_msgs.msg import ByteMultiArray  # noqa: F401
        return True
    except Exception:
        return False


def encode_npz_payload(tiles: np.ndarray, bounds: np.ndarray, roi: tuple, timestamp: str, mode: str) -> bytes:
    buf = io.BytesIO()
    np.savez_compressed(
        buf,
        tiles=tiles,
        tile_bounds_zyx=bounds,
        roi=np.array(roi, dtype=np.int32),
        timestamp=timestamp,
        mode=mode,
    )
    return buf.getvalue()


def main():
    if not ros2_available():
        raise SystemExit(
            "ROS2 not available. Install ROS2 + rclpy + std_msgs, then rerun.\n"
            "This module is optional and does not affect core CIVD."
        )

    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import ByteMultiArray

    from civd.export_submap import export_submap

    class CIVDPublisher(Node):
        def __init__(self):
            super().__init__("civd_submap_publisher")
            self.pub = self.create_publisher(ByteMultiArray, "/civd/submap_delta", 10)

            # Produce a delta export from existing CIVD timepack
            meta = export_submap(
                "data/civd_time/t001/index.json",
                (128, 128, 160),
                40,
                mode="delta",
                out_dir="exports",
            )

            npz = np.load(meta["npz_path"], allow_pickle=True)
            payload = encode_npz_payload(
                npz["tiles"],
                npz["tile_bounds_zyx"],
                tuple(npz["roi"].tolist()),
                meta["timestamp"],
                meta["mode"],
            )

            # Minimal header (optional) — keep it simple
            header = {
                "schema": "civd.ros2.submap_delta.v1",
                "timestamp": meta["timestamp"],
                "mode": meta["mode"],
                "roi": list(tuple(npz["roi"].tolist())),
                "tile_count": int(npz["tiles"].shape[0]),
                "bytes": len(payload),
            }
            self.get_logger().info("Publishing one delta message: " + json.dumps(header))

            msg = ByteMultiArray()
            msg.data = list(payload)  # ByteMultiArray stores uint8[]; Python list is acceptable
            self.pub.publish(msg)

            self.get_logger().info("Published /civd/submap_delta and exiting.")

    rclpy.init()
    node = CIVDPublisher()
    rclpy.spin_once(node, timeout_sec=0.5)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
