#!/usr/bin/env python3
# encoding: utf-8
"""
colmap2opensfm.py
直接将 COLMAP 输出转换为 OpenSfM 格式
不需要通过 ContextCapture XML 中间格式

特性:
- 自动从图像 EXIF 提取 GPS 原点
- 保留完整相机参数 (fx, fy 不求平均)
- 正确处理切向畸变参数 (p1, p2)
- 支持 OPENCV, SIMPLE_RADIAL, RADIAL, PINHOLE 模型
"""

import json
import os
import sys
import numpy as np
from scipy.spatial.transform import Rotation as R
import csv

# 尝试导入 PIL 用于 GPS 提取
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("警告: 未安装 PIL/Pillow，将跳过 GPS 提取")

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
    if not HAS_PIL:
        return None

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
        pass

    return None

def find_closest_image_to_origin(images, cameras):
    """找到最接近原点 (0,0,0) 的图像"""
    closest_img = None
    min_distance = float('inf')

    for img_id, img in images.items():
        # 计算相机中心
        rotation = R.from_quat([img['qx'], img['qy'], img['qz'], img['qw']])
        R_wc = rotation.as_matrix()
        t_wc = np.array([img['tx'], img['ty'], img['tz']])
        center = -R_wc.T @ t_wc

        # 计算距离
        distance = np.linalg.norm(center)

        if distance < min_distance:
            min_distance = distance
            closest_img = img

    return closest_img

def extract_gps_origin(images, cameras, image_dir):
    """从最接近原点的图像提取 GPS 数据"""
    if not image_dir or not HAS_PIL:
        return None

    print("  查找最接近原点的图像...")
    closest_img = find_closest_image_to_origin(images, cameras)

    if not closest_img:
        return None

    image_name = os.path.basename(closest_img['name'])
    image_path = os.path.join(image_dir, image_name)

    # 如果图像不存在，尝试在子目录中查找
    if not os.path.exists(image_path):
        for root, dirs, files in os.walk(image_dir):
            if image_name in files:
                image_path = os.path.join(root, image_name)
                break

    if not os.path.exists(image_path):
        print(f"  警告: 找不到图像 {image_path}")
        return None

    print(f"  尝试提取 GPS: {image_name}")
    gps_data = get_exif_gps(image_path)

    if gps_data:
        print(f"  ✅ 成功提取 GPS 原点:")
        print(f"     纬度: {gps_data['latitude']:.8f}")
        print(f"     经度: {gps_data['longitude']:.8f}")
        print(f"     高度: {gps_data['altitude']:.3f} 米")
    else:
        print(f"  ⚠️  未能提取 GPS 数据")

    return gps_data

def read_cameras(colmap_dir):
    """读取 cameras.txt 文件"""
    cameras_file = os.path.join(colmap_dir, 'cameras.txt')
    cameras = {}

    with open(cameras_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            camera_id = int(parts[0])
            model = parts[1]
            width = int(parts[2])
            height = int(parts[3])

            # 提取相机参数
            if model.startswith('OPENCV'):
                fx = float(parts[4])
                fy = float(parts[5])
                cx = float(parts[6])
                cy = float(parts[7])
                k1 = float(parts[8]) if len(parts) > 8 else 0.0
                k2 = float(parts[9]) if len(parts) > 9 else 0.0
                p1 = float(parts[10]) if len(parts) > 10 else 0.0
                p2 = float(parts[11]) if len(parts) > 11 else 0.0
                k3 = float(parts[12]) if len(parts) > 12 else 0.0
            elif model == 'SIMPLE_RADIAL':
                f = float(parts[4])
                fx = fy = f
                cx = float(parts[5])
                cy = float(parts[6])
                k1 = float(parts[7]) if len(parts) > 7 else 0.0
                k2 = p1 = p2 = k3 = 0.0
            elif model == 'RADIAL':
                f = float(parts[4])
                fx = fy = f
                cx = float(parts[5])
                cy = float(parts[6])
                k1 = float(parts[7]) if len(parts) > 7 else 0.0
                k2 = float(parts[8]) if len(parts) > 8 else 0.0
                p1 = p2 = k3 = 0.0
            elif model == 'PINHOLE':
                fx = float(parts[4])
                fy = float(parts[5])
                cx = float(parts[6])
                cy = float(parts[7])
                k1 = k2 = p1 = p2 = k3 = 0.0
            else:
                raise ValueError(f"Unsupported camera model: {model}")

            cameras[camera_id] = {
                'model': model,
                'width': width,
                'height': height,
                'fx': fx,
                'fy': fy,
                'cx': cx,
                'cy': cy,
                'k1': k1,
                'k2': k2,
                'p1': p1,
                'p2': p2,
                'k3': k3
            }

    return cameras

def read_images(colmap_dir):
    """读取 images.txt 文件"""
    images_file = os.path.join(colmap_dir, 'images.txt')
    images = {}

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

        # 读取下一行的 2D 点
        i += 1
        points2d = {}
        if i < len(lines):
            line2 = lines[i].strip()
            if line2 and not line2.startswith('#'):
                parts2 = line2.split()
                for j in range(0, len(parts2), 3):
                    if j + 2 < len(parts2):
                        x = float(parts2[j])
                        y = float(parts2[j+1])
                        point3d_id = int(parts2[j+2])
                        if point3d_id != -1:
                            points2d[point3d_id] = (x, y)

        images[image_id] = {
            'id': image_id,
            'name': name,
            'camera_id': camera_id,
            'qw': qw, 'qx': qx, 'qy': qy, 'qz': qz,
            'tx': tx, 'ty': ty, 'tz': tz,
            'points2d': points2d
        }

        i += 1

    return images

def read_points3D(colmap_dir):
    """读取 points3D.txt 文件"""
    points_file = os.path.join(colmap_dir, 'points3D.txt')
    points = {}

    with open(points_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            point_id = int(parts[0])
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            r, g, b = int(parts[4]), int(parts[5]), int(parts[6])
            error = float(parts[7]) if len(parts) > 7 else 0.0

            # 读取观测数据
            observations = []
            for j in range(8, len(parts), 2):
                if j + 1 < len(parts):
                    image_id = int(parts[j])
                    point2d_idx = int(parts[j+1])
                    observations.append((image_id, point2d_idx))

            points[point_id] = {
                'xyz': [x, y, z],
                'rgb': [r, g, b],
                'error': error,
                'observations': observations
            }

    return points

def convert_to_opensfm(cameras, images, points3D, output_dir, image_dir):
    """转换为 OpenSfM 格式"""

    os.makedirs(output_dir, exist_ok=True)

    # 提取 GPS 原点
    print("提取 GPS 原点...")
    gps_origin = extract_gps_origin(images, cameras, image_dir)

    if not gps_origin:
        print("  使用默认值 (0, 0, 0)")
        gps_origin = {"latitude": 0, "longitude": 0, "altitude": 0}

    # 归一化参数
    max_dim = max(cameras[1]['width'], cameras[1]['height'])
    normalizer = max_dim

    # 1. 生成 camera_models.json
    camera_models = {}
    for cam_id, cam in cameras.items():
        model_key = f"v1 OpenSfM - AT {cam['width']} {cam['height']} brown {cam['fx']/normalizer:.4f}"

        camera_models[model_key] = {
            "projection_type": "brown",
            "width": cam['width'],
            "height": cam['height'],
            "focal_x": cam['fx'] / normalizer,
            "focal_y": cam['fy'] / normalizer,
            "c_x": (cam['cx'] - (cam['width'] - 1) / 2) / normalizer,
            "c_y": (cam['cy'] - (cam['height'] - 1) / 2) / normalizer,
            "k1": cam['k1'],
            "k2": cam['k2'],
            "p1": cam['p1'],
            "p2": cam['p2'],
            "k3": cam['k3']
        }

    with open(os.path.join(output_dir, 'camera_models.json'), 'w') as f:
        json.dump(camera_models, f, indent=2)

    # 2. 生成 reconstruction.json
    shots = {}
    recon_points = {}

    for img_id, img in images.items():
        cam = cameras[img['camera_id']]
        model_key = f"v1 OpenSfM - AT {cam['width']} {cam['height']} brown {cam['fx']/normalizer:.4f}"

        # 转换四元数到旋转矩阵
        rotation = R.from_quat([img['qx'], img['qy'], img['qz'], img['qw']])
        rotation_matrix = rotation.as_matrix()

        # 转换为旋转向量
        r_vector = rotation.as_rotvec().tolist()

        # 计算相机中心
        # COLMAP 存储的是 world_to_cam 的平移，需要计算相机中心
        R_wc = rotation_matrix  # world to camera
        t_wc = np.array([img['tx'], img['ty'], img['tz']])
        center = -R_wc.T @ t_wc

        # 计算相对于参考点的 GPS 位置
        gps_position = center.tolist()

        shot_data = {
            "ori_rotation_matrix": rotation_matrix.tolist(),
            "photo_id": str(img_id),
            "rotation": r_vector,
            "translation": t_wc.tolist(),
            "camera": model_key,
            "orientation": 1,
            "capture_time": 0,
            "gps_dop": 0.0422,
            "gps_position": gps_position,
            "image_path": os.path.basename(img['name']),
            "vertices": [],
            "faces": [],
            "scale": 1.0,
            "covariance": [],
            "merge_cc": 0
        }

        shots[os.path.basename(img['name'])] = shot_data

    # 处理 3D 点
    for point_id, point in points3D.items():
        recon_points[str(point_id)] = {
            "color": point['rgb'],
            "coordinates": point['xyz']
        }

    reconstruction = {
        "cameras": camera_models,
        "shots": shots,
        "points": recon_points,
        "reference_lla": gps_origin
    }

    with open(os.path.join(output_dir, 'reconstruction.json'), 'w') as f:
        json.dump([reconstruction], f, indent=2)

    # 3. 生成 reference_lla.json
    with open(os.path.join(output_dir, 'reference_lla.json'), 'w') as f:
        json.dump(gps_origin, f, indent=2)

    # 4. 生成 image_list.json
    image_list = [os.path.basename(img['name']) for img in images.values()]
    with open(os.path.join(output_dir, 'image_list.json'), 'w') as f:
        json.dump(image_list, f, indent=2)

    # 5. 生成 converted_tracks.csv
    with open(os.path.join(output_dir, 'converted_tracks.csv'), 'w', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        for img_id, img in images.items():
            image_name = os.path.basename(img['name'])
            for point3d_id, (x, y) in img['points2d'].items():
                # 归一化坐标
                u = (x - (cameras[img['camera_id']]['width'] - 1) / 2) / normalizer
                v = (y - (cameras[img['camera_id']]['height'] - 1) / 2) / normalizer

                point = points3D.get(point3d_id)
                if point:
                    r, g, b = point['rgb']
                    writer.writerow([
                        image_name,
                        point3d_id,
                        0,  # feature ID
                        u,
                        v,
                        0,  # scale
                        r, g, b,
                        -1, -1  # extra fields
                    ])

    print(f"转换完成！")
    print(f"输出目录: {output_dir}")
    print(f"图像数量: {len(images)}")
    print(f"3D点数量: {len(points3D)}")
    print(f"相机数量: {len(cameras)}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python colmap2opensfm.py <colmap_sparse_dir> <output_dir> [image_dir]")
        print("  colmap_sparse_dir: COLMAP sparse 目录 (包含 cameras.txt, images.txt, points3D.txt)")
        print("  output_dir: OpenSfM 输出目录")
        print("  image_dir: 图像目录 (可选)")
        sys.exit(1)

    colmap_dir = sys.argv[1]
    output_dir = sys.argv[2]
    image_dir = sys.argv[3] if len(sys.argv) > 3 else None

    print("读取 COLMAP 数据...")
    cameras = read_cameras(colmap_dir)
    images = read_images(colmap_dir)
    points3D = read_points3D(colmap_dir)

    print(f"读取到 {len(cameras)} 个相机")
    print(f"读取到 {len(images)} 张图像")
    print(f"读取到 {len(points3D)} 个 3D 点")

    print("转换为 OpenSfM 格式...")
    convert_to_opensfm(cameras, images, points3D, output_dir, image_dir)
