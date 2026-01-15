#!/usr/bin/env python3
"""
从 COLMAP 空三结果中提取 ENU 坐标系原点对应的 GPS 坐标

原理:
- COLMAP model_aligner 使用 --alignment_type enu 时，会将模型转换到 ENU 坐标系
- 原点通常是某个参考图像的位置，或者所有图像 GPS 的中心
- 我们可以通过以下方法找到原点对应的 GPS:
  1. 从 images.txt 中找到位置最接近 (0,0,0) 的图像
  2. 提取该图像的 EXIF GPS 数据
  3. 更新 reference_lla.json
"""

import os
import sys
import json
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def dms_to_decimal(degrees, minutes, seconds):
    """将 DMS 格式转换为十进制"""
    try:
        d = float(degrees)
        m = float(minutes)
        s = float(seconds)
        return d + m/60 + s/3600
    except:
        return 0.0

def get_exif_gps(image_path):
    """从图像提取 EXIF GPS 数据"""
    try:
        image = Image.open(image_path)
        exif = image._getexif()

        if not exif:
            return None

        # 查找 GPS Info
        gps_info = None
        for tag, value in exif.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == "GPSInfo":
                gps_info = value
                break

        if not gps_info:
            return None

        # 提取 GPS 数据
        gps_data = {}

        # 纬度
        if 2 in gps_info and 1 in gps_info:
            lat = dms_to_decimal(*gps_info[2])
            lat_ref = gps_info[1]
            if lat_ref == 'S':
                lat = -lat
            gps_data['latitude'] = lat

        # 经度
        if 4 in gps_info and 3 in gps_info:
            lon = dms_to_decimal(*gps_info[4])
            lon_ref = gps_info[3]
            if lon_ref == 'W':
                lon = -lon
            gps_data['longitude'] = lon

        # 高度
        if 6 in gps_info:
            alt = float(gps_info[6])
            if 5 in gps_info and gps_info[5] == b'\x01':
                alt = -alt  # 低于海平面
            gps_data['altitude'] = alt

        if len(gps_data) == 3:
            return gps_data

    except Exception as e:
        print(f"警告: 读取 {image_path} GPS 数据失败: {e}")

    return None

def read_images_txt(colmap_dir):
    """读取 images.txt 文件，返回图像位置信息"""
    images_file = os.path.join(colmap_dir, 'images.txt')

    if not os.path.exists(images_file):
        raise FileNotFoundError(f"找不到 {images_file}")

    images = []
    with open(images_file, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith('#'):
            i += 1
            continue

        parts = line.split()
        image_id = int(parts[0])
        qw, qx, qy, qz = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
        tx, ty, tz = float(parts[5]), float(parts[6]), float(parts[7])
        camera_id = int(parts[8])
        name = parts[9]

        # 计算相机中心
        from scipy.spatial.transform import Rotation as R
        rotation = R.from_quat([qx, qy, qz, qw])
        R_wc = rotation.as_matrix()
        t_wc = np.array([tx, ty, tz])
        center = -R_wc.T @ t_wc

        images.append({
            'id': image_id,
            'name': name,
            'center': center,
            'tx': tx, 'ty': ty, 'tz': tz
        })

        i += 2  # 跳过下一行的 2D 点数据

    return images

def find_origin_images(images, top_n=10):
    """找到位置最接近原点的图像"""
    # 计算每个图像到原点的距离
    for img in images:
        img['distance'] = np.linalg.norm(img['center'])

    # 按距离排序
    images_sorted = sorted(images, key=lambda x: x['distance'])

    return images_sorted[:top_n]

def extract_gps_origin(colmap_dir, image_dir, output_file=None):
    """提取原点对应的 GPS 坐标"""
    print("=" * 80)
    print("从 COLMAP 空三结果提取 ENU 原点对应的 GPS 坐标")
    print("=" * 80)

    # 1. 读取 images.txt
    print(f"\n读取: {colmap_dir}/images.txt")
    images = read_images_txt(colmap_dir)
    print(f"找到 {len(images)} 张图像")

    # 2. 找到最接近原点的图像
    print("\n查找位置最接近原点 (0,0,0) 的图像...")
    origin_images = find_origin_images(images, top_n=10)

    print(f"\n前 10 张最接近原点的图像:")
    print(f"{'排名':<5} {'图像名':<40} {'X':>12} {'Y':>12} {'Z':>12} {'距离':>12}")
    print("-" * 100)
    for i, img in enumerate(origin_images, 1):
        print(f"{i:<5} {img['name']:<40} {img['center'][0]:>12.3f} {img['center'][1]:>12.3f} {img['center'][2]:>12.3f} {img['distance']:>12.3f}")

    # 3. 提取第一张图像的 GPS
    print("\n尝试从最接近原点的图像提取 GPS 数据...")
    closest_image = origin_images[0]
    image_path = os.path.join(image_dir, closest_image['name'])

    if not os.path.exists(image_path):
        # 尝试在 image_dir 的子目录中查找
        image_name = os.path.basename(closest_image['name'])
        for root, dirs, files in os.walk(image_dir):
            if image_name in files:
                image_path = os.path.join(root, image_name)
                break

    print(f"图像路径: {image_path}")
    gps_data = get_exif_gps(image_path)

    if gps_data:
        print(f"\n✅ 成功提取 GPS 数据:")
        print(f"  纬度: {gps_data['latitude']:.8f}")
        print(f"  经度: {gps_data['longitude']:.8f}")
        print(f"  高度: {gps_data['altitude']:.3f} 米")

        # 4. 更新 reference_lla.json
        if output_file:
            print(f"\n更新: {output_file}")
            with open(output_file, 'w') as f:
                json.dump(gps_data, f, indent=2)
            print(f"✅ GPS 数据已保存到 {output_file}")

            # 同时验证
            with open(output_file) as f:
                saved_data = json.load(f)
            print(f"\n验证 reference_lla.json 内容:")
            print(json.dumps(saved_data, indent=2))

        return gps_data
    else:
        print(f"\n❌ 未能提取 GPS 数据")
        print("可能原因:")
        print("  - 图像没有 EXIF GPS 数据")
        print("  - 图像路径不正确")

        # 尝试其他图像
        print(f"\n尝试其他图像...")
        for img in origin_images[1:6]:
            image_path = os.path.join(image_dir, os.path.basename(img['name']))
            if not os.path.exists(image_path):
                for root, dirs, files in os.walk(image_dir):
                    if os.path.basename(img['name']) in files:
                        image_path = os.path.join(root, os.path.basename(img['name']))
                        break

            if os.path.exists(image_path):
                gps_data = get_exif_gps(image_path)
                if gps_data:
                    print(f"\n✅ 从第 {images.index(img)+1} 张图像提取到 GPS 数据:")
                    print(f"  图像: {img['name']}")
                    print(f"  纬度: {gps_data['latitude']:.8f}")
                    print(f"  经度: {gps_data['longitude']:.8f}")
                    print(f"  高度: {gps_data['altitude']:.3f} 米")

                    if output_file:
                        with open(output_file, 'w') as f:
                            json.dump(gps_data, f, indent=2)
                        print(f"\n✅ GPS 数据已保存到 {output_file}")

                    return gps_data

        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_gps_origin.py <colmap_sparse_dir> <image_dir> [output_file]")
        print("  colmap_sparse_dir: COLMAP sparse 目录 (包含 images.txt)")
        print("  image_dir: 图像目录")
        print("  output_file: 输出的 reference_lla.json 文件路径 (可选)")
        sys.exit(1)

    colmap_dir = sys.argv[1]
    image_dir = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    extract_gps_origin(colmap_dir, image_dir, output_file)

if __name__ == '__main__':
    main()
