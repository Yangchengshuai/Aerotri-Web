#!/usr/bin/env python3
"""Check cameras.bin file to see camera model IDs."""
import struct
import sys

cameras_bin = sys.argv[1] if len(sys.argv) > 1 else "/root/work/aerotri-web/data/outputs/5de94105-1eb3-453c-89dc-71d6bde5100f/merged/sparse/0/cameras.bin"

model_map = {
    0: "SIMPLE_PINHOLE",
    1: "PINHOLE",
    2: "SIMPLE_RADIAL",
    3: "RADIAL",
    4: "OPENCV",
    5: "OPENCV_FISHEYE",
    6: "FULL_OPENCV",
    7: "FOV",
    8: "SIMPLE_RADIAL_FISHEYE",
    9: "RADIAL_FISHEYE",
    10: "THIN_PRISM_FISHEYE",
}

with open(cameras_bin, "rb") as f:
    num_cameras = struct.unpack("<Q", f.read(8))[0]
    print(f"Number of cameras: {num_cameras}")
    
    for i in range(num_cameras):
        camera_id = struct.unpack("<I", f.read(4))[0]
        model_id = struct.unpack("<I", f.read(4))[0]
        width = struct.unpack("<Q", f.read(8))[0]
        height = struct.unpack("<Q", f.read(8))[0]
        num_params = struct.unpack("<Q", f.read(8))[0]
        params = struct.unpack(f"<{num_params}d", f.read(8 * num_params))
        
        model_name = model_map.get(model_id, f"UNKNOWN({model_id})")
        print(f"Camera {camera_id}: model={model_id} ({model_name}), width={width}, height={height}, params={params}")


