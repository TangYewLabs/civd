\# CIVD Extensions (Optional)



These modules extend CIVD beyond the Phase E core. They are optional and may require extra dependencies.



\## G1 — ROS2 Adapter (Optional)

Folder: `bridge\_ros2/`



Purpose:

\- Publish CIVD delta submaps on a ROS2 topic `/civd/submap\_delta`

\- Subscribe and reconstruct ROI downstream



Status:

\- Adapter code exists and fails gracefully if ROS2 is not installed.

\- Core CIVD remains runnable without ROS2.



Run:

```powershell

python -m bridge\_ros2.sub

python -m bridge\_ros2.pub



