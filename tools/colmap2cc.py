#!/usr/bin/env python3
# encoding: utf-8
"""
colmap2cc_opencv.py
将 COLMAP 输出 (cameras.txt, images.txt, points3D.txt) 转换为 ContextCapture BlocksExchange (block_opensfm.xml)
- 针对 CAMERA MODEL = OPENCV / OPENCV4
- 修正了位姿（相机中心）计算与坐标轴交换（COLMAP -> CC）
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import numpy as np
from scipy.spatial.transform import Rotation as R
import sys
import os

def init_root():
    root = ET.Element('BlocksExchange')
    root.set('version', '3.2')

    spatial_reference_systems = ET.SubElement(root, 'SpatialReferenceSystems')

    srs_wgs84 = ET.SubElement(spatial_reference_systems, 'SRS')
    ET.SubElement(srs_wgs84, 'Id').text = '1'
    ET.SubElement(srs_wgs84, 'Name').text = 'WGS 84 (EPSG:4326)'
    ET.SubElement(srs_wgs84, 'Definition').text = 'WGS84'
    
    srs_local = ET.SubElement(spatial_reference_systems, 'SRS')
    ET.SubElement(srs_local, 'Id').text = '0'
    ET.SubElement(srs_local, 'Name').text = 'Local Space'
    ET.SubElement(srs_local, 'Definition').text = ''

    block = ET.SubElement(root, 'Block')
    ET.SubElement(block, 'Name').text = 'OpenSfM - AT'
    ET.SubElement(block, 'Description').text = 'OpenSfM converts to CC'
    ET.SubElement(block, 'SRSId').text = '0'

    ET.SubElement(block, 'Photogroups')
    ET.SubElement(block, 'TiePoints')

    return root

def add_photogroup(_root, cam_data, sensor_size, phg_name):
    photogroups = _root.find('Block').find('Photogroups')
    photogroup = ET.SubElement(photogroups, 'Photogroup')
    ET.SubElement(photogroup, 'Name').text = phg_name
    ET.SubElement(photogroup, 'ManualOpticalParams').text = 'true'
    ET.SubElement(photogroup, 'ManualPose').text = 'true'
    imagedim = ET.SubElement(photogroup, 'ImageDimensions')
    ET.SubElement(imagedim, 'Width').text = str(cam_data['width'])
    ET.SubElement(imagedim, 'Height').text = str(cam_data['height'])
    ET.SubElement(photogroup, 'CameraModelType').text = 'Perspective'
    ET.SubElement(photogroup, 'CameraModelBand').text = 'Visible'
    ET.SubElement(photogroup, 'FocalLengthPixels').text = str(cam_data['fx'])
    # ET.SubElement(photogroup, 'SensorSize').text = str(cam_data['sensor_size'])
    # 我们将目标坐标系写成 XRightYDown，适配colmap
    ET.SubElement(photogroup, 'CameraOrientation').text = 'XRightYDown'
    principal = ET.SubElement(photogroup, 'PrincipalPoint')
    ET.SubElement(principal, 'x').text = str(cam_data.get('cx', cam_data['width']/2.0))
    ET.SubElement(principal, 'y').text = str(cam_data.get('cy', cam_data['height']/2.0))

    # Distortion mapping from OpenCV -> CC Brown-Conrady fields
    dist = ET.SubElement(photogroup, 'Distortion')
    # assign defaults
    k1 = cam_data.get('k1', 0.0)
    k2 = cam_data.get('k2', 0.0)
    p1 = cam_data.get('p1', 0.0)
    p2 = cam_data.get('p2', 0.0)
    k3 = cam_data.get('k3', 0.0)
    ET.SubElement(dist, 'K1').text = str(k1)
    ET.SubElement(dist, 'K2').text = str(k2)
    ET.SubElement(dist, 'K3').text = str(k3)
    ET.SubElement(dist, 'P1').text = str(p1)
    ET.SubElement(dist, 'P2').text = str(p2)

    ET.SubElement(photogroup, 'AspectRatio').text = str(cam_data['fy']/cam_data['fx'])
    ET.SubElement(photogroup, 'Skew').text = '0'

def add_photo(_root, image_data, photogroup_name, image_dir):
    photogroups = _root.find('Block').find('Photogroups')
    photogroup = None
    for pg in photogroups.findall('Photogroup'):
        if pg.find('Name').text == photogroup_name:
            photogroup = pg
            break
    if photogroup is None:
        raise RuntimeError(f"Photogroup {photogroup_name} not found")

    photo = ET.SubElement(photogroup, 'Photo')
    ET.SubElement(photo, 'Id').text = str(image_data['Id'])
    ET.SubElement(photo, 'ImagePath').text = os.path.join(image_dir, image_data['Name'])
    ET.SubElement(photo, 'Component').text = '1'

    pose = ET.SubElement(photo, 'Pose')
    rotation = ET.SubElement(pose, 'Rotation')

    Rm = image_data['Rotation_mat']  # 3x3 numpy
    # write row-major elements M_00 ... M_22
    for i in range(3):
        for j in range(3):
            ET.SubElement(rotation, f'M_{i}{j}').text = str(float(Rm[i, j]))
    ET.SubElement(rotation, 'Accurate').text = 'true'

    center = ET.SubElement(pose, 'Center')
    ET.SubElement(center, 'x').text = str(float(image_data['Center']['x']))
    ET.SubElement(center, 'y').text = str(float(image_data['Center']['y']))
    ET.SubElement(center, 'z').text = str(float(image_data['Center']['z']))
    ET.SubElement(center, 'Accurate').text = 'true'

def add_tiepoint(_root, pt):
    tiepoints = _root.find('Block').find('TiePoints')
    tp = ET.SubElement(tiepoints, 'TiePoint')
    pos = ET.SubElement(tp, 'Position')
    ET.SubElement(pos, 'x').text = str(pt['Position']['x'])
    ET.SubElement(pos, 'y').text = str(pt['Position']['y'])
    ET.SubElement(pos, 'z').text = str(pt['Position']['z'])
    color = ET.SubElement(tp, 'Color')
    ET.SubElement(color, 'Red').text = str(pt['Color']['Red'])
    ET.SubElement(color, 'Green').text = str(pt['Color']['Green'])
    ET.SubElement(color, 'Blue').text = str(pt['Color']['Blue'])
    for m in pt['Measurement']:
        meas = ET.SubElement(tp, 'Measurement')
        ET.SubElement(meas, 'PhotoId').text = str(m['PhotoId'])
        ET.SubElement(meas, 'x').text = str(m['x'])
        ET.SubElement(meas, 'y').text = str(m['y'])

def pretty_write(root, path):
    xmlstr = minidom.parseString(ET.tostring(root, encoding='utf-8')).toprettyxml(indent='\t')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(xmlstr)

# -----------------------
# main
# -----------------------
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python colmap2cc_opencv.py <colmap_dir/> <cc_photos_dir/> <sensor_size_mm> [filter_flag]")
        sys.exit(1)

    directory_colmap = sys.argv[1]
    directory_ccphotos = sys.argv[2]
    flag_filter = sys.argv[3] if len(sys.argv) > 3 else None

    # directory_colmap = "data/test/sparse/exp6/geo_model"
    # directory_ccphotos = "data/city1-CQ02-441-bagcp-riggcp-adj/images"
    # flag_filter = None

    cameras_txt_path  = os.path.join(directory_colmap, 'cameras.txt')
    images_txt_path   = os.path.join(directory_colmap, 'images.txt')
    points3D_txt_path = os.path.join(directory_colmap, 'points3D.txt')
    output_xml_path   = os.path.join(directory_colmap, 'block_opensfm.xml')

    # --- read cameras.txt ---
    cameras_data = {}
    with open(cameras_txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() == '' or line[0] == '#':
                continue
            parts = line.strip().split()
            cid = parts[0]
            model = parts[1]
            width = int(parts[2]); height = int(parts[3])
            # OPENCV format: fx fy cx cy k1 k2 p1 p2 [k3 ...]
            if model.upper().startswith('OPENCV'):
                fx = float(parts[4])
                fy = float(parts[5])
                cx = float(parts[6])
                cy = float(parts[7])
                # remaining are distortion
                remaining = parts[8:]
                k1 = float(remaining[0]) if len(remaining) > 0 else 0.0
                k2 = float(remaining[1]) if len(remaining) > 1 else 0.0
                p1 = float(remaining[2]) if len(remaining) > 2 else 0.0
                p2 = float(remaining[3]) if len(remaining) > 3 else 0.0
                k3 = float(remaining[4]) if len(remaining) > 4 else 0.0
                # use focal in pixels: average fx,fy
                focal = (fx + fy) / 2.0
                cam = {'id': cid, 'model': model, 'width': width, 'height': height,
                       'fx': fx, 'fy': fy, 'cx': cx, 'cy': cy, 'focal': focal,
                       'k1': k1, 'k2': k2, 'p1': p1, 'p2': p2, 'k3': k3}
            elif model.upper() == 'SIMPLE_RADIAL':
                # SIMPLE_RADIAL: f, cx, cy, k1
                focal = float(parts[4])
                cx = float(parts[5])
                cy = float(parts[6])
                k1 = float(parts[7]) if len(parts) > 7 else 0.0
                cam = {'id': cid, 'model': model, 'width': width, 'height': height,
                       'fx': focal, 'fy': focal, 'cx': cx, 'cy': cy, 'focal': focal,
                       'k1': k1, 'k2': 0.0, 'p1': 0.0, 'p2': 0.0, 'k3': 0.0}
            elif model.upper() == 'RADIAL':
                # RADIAL: f, cx, cy, k1, k2
                focal = float(parts[4])
                cx = float(parts[5])
                cy = float(parts[6])
                k1 = float(parts[7]) if len(parts) > 7 else 0.0
                k2 = float(parts[8]) if len(parts) > 8 else 0.0
                cam = {'id': cid, 'model': model, 'width': width, 'height': height,
                       'fx': focal, 'fy': focal, 'cx': cx, 'cy': cy, 'focal': focal,
                       'k1': k1, 'k2': k2, 'p1': 0.0, 'p2': 0.0, 'k3': 0.0}
            elif model.upper() == 'PINHOLE':
                # PINHOLE: fx, fy, cx, cy
                fx = float(parts[4])
                fy = float(parts[5])
                cx = float(parts[6])
                cy = float(parts[7])
                focal = (fx + fy) / 2.0
                cam = {'id': cid, 'model': model, 'width': width, 'height': height,
                       'fx': fx, 'fy': fy, 'cx': cx, 'cy': cy, 'focal': focal,
                       'k1': 0.0, 'k2': 0.0, 'p1': 0.0, 'p2': 0.0, 'k3': 0.0}
            elif model.upper() == "FULL_OPENCV":
                # FULL_OPENCV: fx fy cx cy k1 k2 p1 p2 k3 k4 k5 k6
                fx = float(parts[4])
                fy = float(parts[5])
                cx = float(parts[6])
                cy = float(parts[7])
                remaining = parts[8:]
                k1 = float(remaining[0]) if len(remaining) > 0 else 0.0
                k2 = float(remaining[1]) if len(remaining) > 1 else 0.0
                p1 = float(remaining[2]) if len(remaining) > 2 else 0.0
                p2 = float(remaining[3]) if len(remaining) > 3 else 0.0
                k3 = float(remaining[4]) if len(remaining) > 4 else 0.0
                focal = (fx + fy) / 2.0
                cam = {'id': cid, 'model': model, 'width': width, 'height': height,
                       'fx': fx, 'fy': fy, 'cx': cx, 'cy': cy, 'focal': focal,
                       'k1': k1, 'k2': k2, 'p1': p1, 'p2': p2, 'k3': k3}
            else:
                # fallback: try to parse common pinhole-like
                focal = float(parts[4])
                cx = float(parts[5]) if len(parts) > 5 else width/2.0
                cy = float(parts[6]) if len(parts) > 6 else height/2.0
                cam = {'id': cid, 'model': model, 'width': width, 'height': height,
                       'fx': focal, 'fy': focal, 'cx': cx, 'cy': cy, 'focal': focal,
                       'k1': 0.0, 'k2': 0.0, 'p1': 0.0, 'p2': 0.0, 'k3': 0.0}
            cameras_data[cid] = cam
            # --------------------------
            # 自动计算 sensor size (mm)
            # --------------------------
            # 使用假设的物理焦距（单位：mm）
            FOCAL_MM = 35.0  # 如有实际相机焦距请修改这里

            for cid, cam in cameras_data.items():
                fx = cam['fx']
                
                # sensor_width_mm = focal_mm / focal_pixel * image_width
                sensor_width_mm = FOCAL_MM / fx * cam['width']
                
                cam['sensor_size'] = sensor_width_mm

    # --- read images.txt ---
    images_data = {}
    flag_odd = True
    current_image = None
    with open(images_txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() == '' or line[0] == '#':
                continue
            parts = line.strip().split()
            if flag_odd:
                # id, qw,qx,qy,qz, tx,ty,tz, camera_id, name
                img = {}
                img_id = int(parts[0])
                qw = float(parts[1]); qx = float(parts[2]); qy = float(parts[3]); qz = float(parts[4])
                tx = float(parts[5]); ty = float(parts[6]); tz = float(parts[7])
                cam_id = parts[8]
                name = parts[9]
                img['Id'] = img_id
                img['quat'] = (qw, qx, qy, qz)
                img['t_wc'] = np.array([tx, ty, tz], dtype=float)
                img['Camera'] = cam_id
                img['Name'] = name
                current_image = img
                flag_odd = False
            else:
                # POINTS2D: groups of (x, y, point3d_id)
                pts2d = {}
                for i in range(0, len(parts), 3):
                    if i + 2 < len(parts):
                        x = float(parts[i]); y = float(parts[i+1]); pid = int(parts[i+2])
                        if pid != -1:
                            pts2d[pid] = (x, y)
                current_image['POINTS2D'] = pts2d
                images_data[current_image['Id']] = current_image
                flag_odd = True

    # --- read points3D.txt ---
    points3D_data = {}
    with open(points3D_txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() == '' or line[0] == '#':
                continue
            parts = line.strip().split()
            pid = int(parts[0])
            xw = float(parts[1]); yw = float(parts[2]); zw = float(parts[3])
            r = int(parts[4]); g = int(parts[5]); b = int(parts[6])
            err = float(parts[7]) if len(parts) > 7 else 0.0
            meas = []
            seen_img_ids = set()
            # remaining are (image_id, point2d_idx) pairs
            for i in range(8, len(parts), 2):
                if i+1 < len(parts):
                    img_id = int(parts[i]); pt2d_idx = int(parts[i+1])
                    if img_id in images_data:
                        # find 2D image coordinate from POINTS2D keyed by point3d id
                        if pid in images_data[img_id].get('POINTS2D', {}):
                            if img_id not in seen_img_ids:
                                x2, y2 = images_data[img_id]['POINTS2D'][pid]
                                meas.append({'PhotoId': img_id, 'x': x2, 'y': y2})
                                seen_img_ids.add(img_id)
                            else:
                                print(f"Warning: duplicate measurement for point {pid} in image {img_id}, skipping.")
            if len(meas) >= 2:
                points3D_data[pid] = {'id': pid,
                                      'Position': {'x': xw, 'y': yw, 'z': zw},
                                      'Color': {'Red': r/255.0, 'Green': g/255.0, 'Blue': b/255.0},
                                      'Error': err,
                                      'Measurement': meas}

    # --- 构建 XML ---
    root = init_root()

    cam_to_phg = {}
    for i, (cam_name, cam) in enumerate(cameras_data.items()):
        phg_name = 'Photogroup ' + str(i + 1)
        cam_to_phg[cam_name] = phg_name
        add_photogroup(root, cam, cam['sensor_size'], phg_name)


    # process images: compute R_cw (camera->world), center C, then convert axes
    for img_id, img in images_data.items():
        qw, qx, qy, qz = img['quat']
        # scipy expects quaternion in [x,y,z,w]
        r_matrix = R.from_quat([qx, qy, qz, qw]).as_matrix()   # this is R_wc (world -> camera) in COLMAP
        t_local = img['t_wc']

        M = np.hstack([np.vstack([r_matrix, np.zeros((3,))]), np.append(t_local, 1).reshape(4, 1)])
        M_inv = np.linalg.inv(M)
        t_world = np.dot(M_inv, np.array([0, 0, 0, 1]))[:3]

        # Save into image dict for writing
        img['Rotation_mat'] = r_matrix
        img['Center'] = {'x': float(t_world[0]), 'y': float(t_world[1]), 'z': float(t_world[2])}

        # also attach principal/other info for measurements (not strictly needed)
        # write photo into xml
        add_photo(root, img, cam_to_phg[img['Camera']], directory_ccphotos)

    # add tie points
    for pid, pt in points3D_data.items():
        add_tiepoint(root, pt)

    # write file
    pretty_write(root, output_xml_path)

    print(f"Successfully converted {len(images_data)} images and {len(points3D_data)} 3D points to CC format")
    print(f"Output saved to: {output_xml_path}")
