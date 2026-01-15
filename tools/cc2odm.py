import xml.etree.ElementTree as ET
import json
import csv
import os
from datetime import datetime
import numpy as np
from pyproj import CRS
from pyproj import Transformer
from pyproj.database import query_utm_crs_info
from pyproj.aoi import AreaOfInterest
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as R
import xml.etree.ElementTree as ET
import argparse
import glob


global_width = 0
global_height = 0
global_normalizer = 0

def extract_camera_model(xml_file):
    """
    提取相机模型数据
    """
    global global_width , global_height , global_normalizer
    tree = ET.parse(xml_file)
    root = tree.getroot()
    camera_models = {}
    for block in root.findall('.//Block'):
        block_name = block.find('Name').text  # 获取块名称
        photogroups = block.findall('.//Photogroup')
        # 获取相机模型的相关数据
        for idx, photogroup in enumerate(photogroups):
            image_dimensions = photogroup.find('ImageDimensions')
            distortion = photogroup.find('Distortion')
            principal_point = photogroup.find('PrincipalPoint')
            global_width = int(image_dimensions.find('Width').text)
            global_height = int(image_dimensions.find('Height').text)
            
            global_normalizer = max(global_width, global_height)

            focal_length_pixels = photogroup.find('FocalLengthPixels')
            if focal_length_pixels is not None and focal_length_pixels.text:
                focal_x = float((float(photogroup.find('FocalLengthPixels').text))/ global_normalizer)
            else:
                focal_x = float(float(photogroup.find('FocalLength').text) / float(photogroup.find('SensorSize').text))
            focal_y = focal_x
            # 创建相机模型的字典
            camera_model = {
                "projection_type": "brown",  # 固定为布朗模型
                "width": int(image_dimensions.find('Width').text),
                "height": int(image_dimensions.find('Height').text),
                "focal_x": focal_x,  # 简单估算X、Y方向的焦距
                "focal_y": focal_y,  # focal_y是否能直接简单相同?
                "c_x": float((float(principal_point.find('x').text)-(global_width-1)/2)/global_normalizer),#相对图像中心点的偏移比例
                "c_y": float((float(principal_point.find('y').text)-(global_height-1)/2)/global_normalizer),
                "k1": float(distortion.find('K1').text),
                "k2": float(distortion.find('K2').text),
                "p1": float(distortion.find('P2').text),
                "p2": float(distortion.find('P1').text),
                "k3": float(distortion.find('K3').text)
            }
            # 生成字典键
            model_key = f"v{idx+1} {block_name} {int(image_dimensions.find('Width').text)} {int(image_dimensions.find('Height').text)} brown {focal_x:.4f}"
            camera_message = model_key
            print(camera_message)
            # 保存到相机模型字典中
            camera_models[model_key] = camera_model

    return camera_models

# utm转84
def convert_utm_to_gps(ori_utm, epsg_code=None):
    """
    将UTM坐标转换回WGS84 GPS坐标

    参数:
    - ori_utm: UTM坐标数组 [easting, northing, altitude]
    - epsg_code: UTM区域的EPSG代码（如EPSG:32650）

    返回:
    - 包含GPS坐标的数组 [latitude, longitude, altitude]
    """
    if epsg_code is None:
        zone_number = 50  # 根据实际情况修改
        epsg_code = 32600 + zone_number  # 默认北半球

    # 定义坐标系
    crs_utm = CRS.from_epsg(epsg_code)
    crs_wgs84 = CRS.from_epsg(4326)

    # 创建转换器
    transformer = Transformer.from_crs(crs_utm, crs_wgs84)

    # 注意顺序：输入 easting, northing → 输出 longitude, latitude
    lat, lon = transformer.transform(ori_utm[0], ori_utm[1])

    return np.array([lat, lon, ori_utm[2]])

# 读取影像数据
def parse_photo_data(photo_elem,ori_utm, camera_model):
    
    """
    从<Photo>元素中提取所需数据，并构建转换后的数据
    """
    photo_id = photo_elem.find(".//Id").text
    # 提取rotation矩阵
    rotation_matrix = np.array([
        [float(photo_elem.find(".//Pose/Rotation/M_00").text), float(photo_elem.find(".//Pose/Rotation/M_01").text), float(photo_elem.find(".//Pose/Rotation/M_02").text)],
        [float(photo_elem.find(".//Pose/Rotation/M_10").text), float(photo_elem.find(".//Pose/Rotation/M_11").text), float(photo_elem.find(".//Pose/Rotation/M_12").text)],
        [float(photo_elem.find(".//Pose/Rotation/M_20").text), float(photo_elem.find(".//Pose/Rotation/M_21").text), float(photo_elem.find(".//Pose/Rotation/M_22").text)]
    ])
    # 恢复旋转向量
    rotation = R.from_matrix(rotation_matrix)
    r_vector = rotation.as_rotvec()
    r_vector = r_vector.tolist()
    # print("ssssssssssssssssss",r_vector,"ssssssssssssssssss")

    # 提取translation (Center)
    t_world = [
        float(photo_elem.find(".//Pose/Center/x").text)- ori_utm[0],
        float(photo_elem.find(".//Pose/Center/y").text)- ori_utm[1],
        float(photo_elem.find(".//Pose/Center/z").text)- ori_utm[2]
    ]

    translation = (-np.dot(rotation_matrix, t_world)).tolist()

    # 将日期时间转换为Unix时间戳
    if photo_elem.find(".//ExifData/DateTimeOriginal"):
        date_time_original = photo_elem.find(".//ExifData/DateTimeOriginal").text
        capture_time = int(datetime.strptime(date_time_original, "%Y-%m-%dT%H:%M:%S").timestamp())
    else:
        capture_time = 0

    # 获取图片相对路径
    image_path = photo_elem.find(".//ImagePath").text
    image_filename = os.path.basename(image_path)

    # # 根据图像的尺寸获取相应的相机模型
    # width = global_width
    # height = global_height
    # focal_length = float(photo_elem.find(".//ExifData/FocalLength").text)

    # 生成对应的JSON数据结构
    photo_data = {
        "shot": {
            image_filename:{
            "ori_rotation_matrix":rotation_matrix.tolist(),
            "photo_id": photo_id,
            "rotation": r_vector,
            "translation": translation,
            "camera": camera_model,  # 使用相机模型数据
            "orientation": 1,  # 固定值
            "capture_time": capture_time,
            "gps_dop": 0.0422,  # 固定值
            "gps_position": t_world,
            "image_path": image_filename,  # 使用相对路径
            "vertices": [],  # 固定为空
            "faces": [],  # 固定为空
            "scale": 1.0,  # 固定值
            "covariance": [],  # 固定为空
            "merge_cc": 0  # 固定值
            }
        }
    }
    return photo_data

# 求连接点
def parse_tie_points(Points, ori_utm):
    points = {}
    for idx, tie_point in enumerate(Points):
        # 获取position数据并减去ori_utm
        position = tie_point.find('Position')
        x = float(position.find('x').text) #经度对应
        y = float(position.find('y').text)
        z = float(position.find('z').text)
        
        # 计算坐标偏移
        coordinates = [
            x - ori_utm[0],  # 减去参考点的东距//
            y - ori_utm[1],  # 减去参考点的北距
            z - ori_utm[2]   # 减去参考点的高度
        ]
        
        # 获取color数据并转换为0-255范围
        color = tie_point.find('Color')
        r = float(color.find('Red').text)
        g = float(color.find('Green').text)
        b = float(color.find('Blue').text)
        
        # 转换为0-255范围的整数
        rgb_color = [
            round(r * 255),
            round(g * 255),
            round(b * 255)
        ]
        
        # 将处理后的数据存入points字典
        point_id = str(idx)  # 使用索引作为ID，从0开始
        points[point_id] = {
            "color": rgb_color,
            "coordinates": coordinates
        }
    
    # 返回最终结果
    return {"points": points}

def save_camera_models_to_json(camera_models, output_file):
    """
    将相机模型数据写入JSON文件
    """
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"Existing file {output_file} removed.")
    with open(output_file, 'w') as json_file:
        json.dump(camera_models, json_file, indent=4)
    print(f"Camera models saved to {output_file}")

def save_reconstruction_to_json(reconstructions, output_file):
    """
    将重建数据写入JSON文件
    """
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"Existing file {output_file} removed.")
    with open(output_file, 'w') as json_file:
        json.dump(reconstructions, json_file, indent=4)
    print(f"Reconstruction data saved to {output_file}")

def generate_measurement_csv(xml_file, csv_path):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # 构建 PhotoId → ImagePath 的映射表
    photo_id_to_path = {}
    photogroups = root.find('Block').find('Photogroups')
    for photogroup in photogroups.findall('Photogroup'):
        for photo in photogroup.findall('Photo'):
            photo_id = int(photo.find('Id').text)
            image_path = photo.find('ImagePath').text
    # 相对路径
            image_filename = os.path.basename(image_path)
            photo_id_to_path[photo_id] = image_filename
    # 准备输出 CSV
    csv_rows = []

    tile_point_id = -1
    tiepoints = root.find('Block').find('TiePoints')
    for tiepoint in tiepoints.findall('TiePoint'):
        tile_point_id += 1
        color_elem = tiepoint.find('Color')
        R = float(color_elem.find('Red').text) * 255
        G = float(color_elem.find('Green').text) * 255
        B = float(color_elem.find('Blue').text) * 255

        measurements = tiepoint.findall('Measurement')
        for m in measurements:
            photo_id = int(m.find('PhotoId').text)
            u = float((float(m.find('x').text)-(global_width-1)/2)/global_normalizer)
            v = float((float(m.find('y').text)-(global_height-1)/2)/global_normalizer)

            image_path = photo_id_to_path.get(photo_id, "UNKNOWN")

            row = [
                image_path,
                tile_point_id,
                0,
                u,
                v,
                0,
                int(R),
                int(G),
                int(B),
                -1,
                -1
            ]
            csv_rows.append(row)


    # 写入 CSV 文件
    if os.path.exists(csv_path):
        os.remove(csv_path)
        print(f"Existing file {csv_path} removed.")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='\t')  # 指定分隔符为制表符
            writer.writerows(csv_rows)

def convert_xml_to_json(xml_file, meta_xml_file, camera_models, reconstruction_file_path, reference_lla_file_path):
    """
    提取图像数据并生成相应的重建JSON文件
    """
    # 解析XML文件
    tree = ET.parse(xml_file)
    root = tree.getroot()
    # warning
    photo_elements = root.findall('.//Photo')
    Points = root.findall('.//TiePoint')

    if os.path.exists(meta_xml_file):
        ori_utm = ET.parse(meta_xml_file).findtext(".//SRSOrigin")
        if ori_utm is not None:
            ori_utm = list(map(float, ori_utm.split(',')))
            wgs84_ori = convert_utm_to_gps(ori_utm)
        else:
            ori_utm = [0, 0, 0]
            wgs84_ori = [0, 0, 0]
    else:
        ori_utm = [0, 0, 0]
        wgs84_ori = [0, 0, 0]
    result = parse_tie_points(Points, ori_utm)
    reference_lla = {"latitude": wgs84_ori[0],
                     "longitude": wgs84_ori[1],
                     "altitude": wgs84_ori[2]} 
       
    reconstructions = {"cameras": camera_models,
        "shots": {},
        **result,
        "reference_lla": {
        "latitude": wgs84_ori[0],   # 直接通过索引访问
        "longitude": wgs84_ori[1],
        "altitude": wgs84_ori[2]
        }
    } 

    photogroups = root.findall('.//Photogroup')
    for idx, (photogroup, camera_model) in enumerate(zip(photogroups, camera_models)):
        for photo_elem in photogroup.findall('.//Photo'):
            photo_data = parse_photo_data(photo_elem, ori_utm, camera_model)
            shot_dict = photo_data["shot"]  # 这是一个形如 {filename: {...}} 的字典
            reconstructions["shots"].update(shot_dict)
    reconstructions = [reconstructions]
    # 保存重建数据到JSON文件
    save_reconstruction_to_json(reconstructions, reconstruction_file_path)
    save_reconstruction_to_json(reference_lla, reference_lla_file_path)

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert BlockExchange XML format to OpenSfM reconstruction.')
    parser.add_argument('--xml_dir', help='Directory containing cc xml data')
    args = parser.parse_args()
    

    xml_file = glob.glob(os.path.join(args.xml_dir, '*block_opensfm.xml'))[0]
    meta_xml = os.path.join(args.xml_dir, 'metadata.xml')

    output_xml_dir = os.path.join(args.xml_dir, xml_file.split('/')[-1].split('.')[0].replace(' ', ''))
    os.makedirs(output_xml_dir, exist_ok=True)
    csv_path = os.path.join(output_xml_dir, 'converted_tracks.csv')
   
    # 提取相机模型
    camera_models = extract_camera_model(xml_file)
    # 保存相机模型数据到JSON文件
    save_camera_models_to_json(camera_models, os.path.join(output_xml_dir, 'camera_models.json'))
    # 提取图像数据并保存为重建JSON文件
    convert_xml_to_json(xml_file, meta_xml, camera_models, os.path.join(output_xml_dir,'reconstruction.json'), os.path.join(output_xml_dir, 'reference_lla.json'))
    generate_measurement_csv(xml_file,csv_path)
        