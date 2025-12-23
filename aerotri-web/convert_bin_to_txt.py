#!/usr/bin/env python3
"""Convert COLMAP binary format to text format."""
import struct
import sys
import os

def convert_cameras_bin_to_txt(bin_path, txt_path):
    """Convert cameras.bin to cameras.txt."""
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
    
    cameras = {}
    with open(bin_path, "rb") as f:
        num_cameras = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_cameras):
            camera_id = struct.unpack("<I", f.read(4))[0]
            model_id = struct.unpack("<I", f.read(4))[0]
            width = struct.unpack("<Q", f.read(8))[0]
            height = struct.unpack("<Q", f.read(8))[0]
            num_params = struct.unpack("<Q", f.read(8))[0]
            params = struct.unpack(f"<{num_params}d", f.read(8 * num_params))
            
            model_name = model_map.get(model_id, f"UNKNOWN_{model_id}")
            cameras[camera_id] = {
                "model": model_name,
                "width": width,
                "height": height,
                "params": params,
            }
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        f.write(f"# Number of cameras: {len(cameras)}\n")
        for cam_id in sorted(cameras.keys()):
            cam = cameras[cam_id]
            params_str = " ".join(str(p) for p in cam["params"])
            f.write(f"{cam_id} {cam['model']} {cam['width']} {cam['height']} {params_str}\n")

def convert_images_bin_to_txt(bin_path, txt_path):
    """Convert images.bin to images.txt."""
    images = {}
    with open(bin_path, "rb") as f:
        num_images = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_images):
            image_id = struct.unpack("<I", f.read(4))[0]
            qw, qx, qy, qz = struct.unpack("<4d", f.read(32))
            tx, ty, tz = struct.unpack("<3d", f.read(24))
            camera_id = struct.unpack("<I", f.read(4))[0]
            
            # Read image name
            name_chars = []
            while True:
                char = f.read(1)
                if char == b"\x00":
                    break
                name_chars.append(char.decode("utf-8"))
            image_name = "".join(name_chars)
            
            # Skip 2D points
            num_points2d = struct.unpack("<Q", f.read(8))[0]
            f.read(num_points2d * 24)  # Skip point data
            
            images[image_id] = {
                "name": image_name,
                "qw": qw, "qx": qx, "qy": qy, "qz": qz,
                "tx": tx, "ty": ty, "tz": tz,
                "camera_id": camera_id,
                "points2d": [],  # We skip 2D points for now
            }
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        f.write("#   POINTS2D[] as (X, Y, IMAGE_ID, POINT2D_IDX)\n")
        f.write(f"# Number of images: {len(images)}, mean observations per image: 0\n")
        for img_id in sorted(images.keys()):
            img = images[img_id]
            f.write(f"{img_id} {img['qw']} {img['qx']} {img['qy']} {img['qz']} "
                   f"{img['tx']} {img['ty']} {img['tz']} {img['camera_id']} {img['name']}\n")
            # Empty 2D points line
            f.write("\n")

def convert_points3d_bin_to_txt(bin_path, txt_path):
    """Convert points3D.bin to points3D.txt."""
    points = {}
    with open(bin_path, "rb") as f:
        num_points = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_points):
            point_id = struct.unpack("<Q", f.read(8))[0]
            x, y, z = struct.unpack("<3d", f.read(24))
            r, g, b = struct.unpack("<3B", f.read(3))
            error = struct.unpack("<d", f.read(8))[0]
            
            track_length = struct.unpack("<Q", f.read(8))[0]
            track = []
            for _ in range(track_length):
                image_id = struct.unpack("<I", f.read(4))[0]
                point2d_idx = struct.unpack("<I", f.read(4))[0]
                track.append((image_id, point2d_idx))
            
            points[point_id] = {
                "x": x, "y": y, "z": z,
                "r": r, "g": g, "b": b,
                "error": error,
                "track": track,
            }
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("# 3D point list with one line of data per point:\n")
        f.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
        f.write(f"# Number of points: {len(points)}, mean track length: 0.0\n")
        for pt_id in sorted(points.keys()):
            pt = points[pt_id]
            track_str = " ".join(f"{img_id} {pt2d_idx}" for img_id, pt2d_idx in pt["track"])
            f.write(f"{pt_id} {pt['x']} {pt['y']} {pt['z']} {pt['r']} {pt['g']} {pt['b']} "
                   f"{pt['error']} {track_str}\n")

if __name__ == "__main__":
    sparse_dir = sys.argv[1] if len(sys.argv) > 1 else "/root/work/aerotri-web/data/outputs/5de94105-1eb3-453c-89dc-71d6bde5100f/merged/sparse/0"
    
    cameras_bin = os.path.join(sparse_dir, "cameras.bin")
    cameras_txt = os.path.join(sparse_dir, "cameras.txt")
    images_bin = os.path.join(sparse_dir, "images.bin")
    images_txt = os.path.join(sparse_dir, "images.txt")
    points_bin = os.path.join(sparse_dir, "points3D.bin")
    points_txt = os.path.join(sparse_dir, "points3D.txt")
    
    if os.path.exists(cameras_bin):
        print(f"Converting {cameras_bin} to {cameras_txt}")
        convert_cameras_bin_to_txt(cameras_bin, cameras_txt)
        print("Done")
    
    if os.path.exists(images_bin):
        print(f"Converting {images_bin} to {images_txt}")
        convert_images_bin_to_txt(images_bin, images_txt)
        print("Done")
    
    if os.path.exists(points_bin):
        print(f"Converting {points_bin} to {points_txt}")
        convert_points3d_bin_to_txt(points_bin, points_txt)
        print("Done")


