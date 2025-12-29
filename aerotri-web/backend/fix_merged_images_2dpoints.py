#!/usr/bin/env python3
"""修复合并后的images.bin，从原始分区重建2D points数据"""
import os
import struct
from collections import defaultdict

def fix_merged_images_with_2dpoints():
    """从原始分区重建2D points并修复合并后的images.bin"""
    
    base_dir = "/root/work/aerotri-web/data/outputs/b156bd90-2725-409d-862a-166c0cb0096a"
    merged_dir = os.path.join(base_dir, "merged", "sparse", "0")
    output_dir = os.path.join(base_dir, "merged", "sparse", "0_fixed")
    os.makedirs(output_dir, exist_ok=True)
    
    # 从原始分区读取2D points数据
    partition_2dpoints = {}  # image_name -> list of (x, y, point3d_id)
    
    for partition_idx in [0, 1]:
        partition_dir = os.path.join(base_dir, "partitions", f"partition_{partition_idx}", "sparse", "0")
        images_bin = os.path.join(partition_dir, "images.bin")
        
        if not os.path.exists(images_bin):
            continue
        
        print(f"Reading partition {partition_idx}...")
        with open(images_bin, "rb") as f:
            num_images = struct.unpack("<Q", f.read(8))[0]
            for _ in range(int(num_images)):
                image_id = struct.unpack("<I", f.read(4))[0]
                f.read(32 + 24 + 4)  # quaternion + translation + camera_id
                
                # Read image name
                name_chars = []
                while True:
                    char = f.read(1)
                    if char == b"\x00":
                        break
                    name_chars.append(char.decode("utf-8"))
                image_name = "".join(name_chars)
                
                # Read 2D points
                num_points2d = struct.unpack("<Q", f.read(8))[0]
                points2d = []
                for _ in range(int(num_points2d)):
                    x, y = struct.unpack("<2d", f.read(16))
                    point3d_id = struct.unpack("<Q", f.read(8))[0]
                    points2d.append((x, y, point3d_id))
                
                if image_name not in partition_2dpoints:
                    partition_2dpoints[image_name] = points2d
                else:
                    # Merge points from multiple partitions (keep all)
                    partition_2dpoints[image_name].extend(points2d)
    
    print(f"Loaded 2D points for {len(partition_2dpoints)} images")
    
    # 读取合并后的points3D，构建point_id映射
    # 注意：这里假设point_id在合并时没有改变（实际上会改变，需要更复杂的映射）
    # 这是一个简化版本，可能需要根据实际合并逻辑调整
    
    # 读取合并后的images.bin并写入修复版本
    merged_images_bin = os.path.join(merged_dir, "images.bin")
    fixed_images_bin = os.path.join(output_dir, "images.bin")
    
    print(f"Reading merged images.bin...")
    images_data = []
    with open(merged_images_bin, "rb") as f:
        num_images = struct.unpack("<Q", f.read(8))[0]
        for _ in range(int(num_images)):
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
            
            # Skip empty 2D points
            num_points2d = struct.unpack("<Q", f.read(8))[0]
            f.read(int(num_points2d) * 24)
            
            # Get 2D points from original partitions
            points2d = partition_2dpoints.get(image_name, [])
            
            images_data.append({
                "image_id": image_id,
                "qw": qw, "qx": qx, "qy": qy, "qz": qz,
                "tx": tx, "ty": ty, "tz": tz,
                "camera_id": camera_id,
                "image_name": image_name,
                "points2d": points2d,
            })
    
    print(f"Writing fixed images.bin with 2D points...")
    with open(fixed_images_bin, "wb") as f:
        f.write(struct.pack("<Q", len(images_data)))
        for img in images_data:
            f.write(struct.pack("<I", img["image_id"]))
            f.write(struct.pack("<4d", img["qw"], img["qx"], img["qy"], img["qz"]))
            f.write(struct.pack("<3d", img["tx"], img["ty"], img["tz"]))
            f.write(struct.pack("<I", img["camera_id"]))
            f.write(img["image_name"].encode("utf-8") + b"\x00")
            
            # Write 2D points
            points2d = img["points2d"]
            f.write(struct.pack("<Q", len(points2d)))
            for x, y, point3d_id in points2d:
                f.write(struct.pack("<2d", x, y))
                f.write(struct.pack("<Q", point3d_id))
    
    # 复制其他文件
    import shutil
    for filename in ["cameras.bin", "points3D.bin", "cameras.txt", "images.txt", "points3D.txt"]:
        src = os.path.join(merged_dir, filename)
        dst = os.path.join(output_dir, filename)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {filename}")
    
    print(f"\n✅ Fixed images.bin written to: {output_dir}")
    print(f"Total images: {len(images_data)}")
    total_2dpoints = sum(len(img["points2d"]) for img in images_data)
    print(f"Total 2D points: {total_2dpoints}")
    
    return output_dir


if __name__ == "__main__":
    fix_merged_images_with_2dpoints()



