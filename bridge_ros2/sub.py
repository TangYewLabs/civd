import io
import numpy as np

def ros2_available() -> bool:
    try:
        import rclpy  # noqa: F401
        from std_msgs.msg import ByteMultiArray  # noqa: F401
        return True
    except Exception:
        return False


def decode_npz_payload(payload: bytes):
    buf = io.BytesIO(payload)
    d = np.load(buf, allow_pickle=True)
    return d


def main():
    if not ros2_available():
        raise SystemExit(
            "ROS2 not available. Install ROS2 + rclpy + std_msgs, then rerun.\n"
            "This module is optional and does not affect core CIVD."
        )

    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import ByteMultiArray

    from benchmark.replay_submap import reconstruct_roi_from_tiles

    class CIVDSubscriber(Node):
        def __init__(self):
            super().__init__("civd_submap_subscriber")
            self.sub = self.create_subscription(ByteMultiArray, "/civd/submap_delta", self.cb, 10)
            self.got = False

        def cb(self, msg: ByteMultiArray):
            payload = bytes(msg.data)
            d = decode_npz_payload(payload)

            tiles = d["tiles"]
            bounds = d["tile_bounds_zyx"]
            roi = tuple(d["roi"].tolist())
            ts = str(d["timestamp"])
            mode = str(d["mode"])

            channels = tiles.shape[-1]
            roi_arr = reconstruct_roi_from_tiles(tiles, bounds, roi, channels)

            self.get_logger().info(
                f"RX ts={ts} mode={mode} tiles={tiles.shape[0]} roi_shape={roi_arr.shape} "
                f"min={float(roi_arr.min()):.3f} max={float(roi_arr.max()):.3f}"
            )
            self.got = True

    rclpy.init()
    node = CIVDSubscriber()

    # Spin until one message arrives (or timeout)
    for _ in range(200):
        rclpy.spin_once(node, timeout_sec=0.05)
        if node.got:
            break

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
