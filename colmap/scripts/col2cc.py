#!/usr/bin/env python3
# encoding: utf-8
"""
col2cc.py

将 COLMAP 文本模型输出 (cameras.txt, images.txt, points3D.txt) 转换为
ContextCapture BlocksExchange XML（常用文件名：block_opensfm.xml）。

功能：
- 导出相机内参/畸变与外参（姿态/相机中心）到 CC BlocksExchange
- 可选导出 TiePoints（默认关闭，避免生成超大 XML/占用过多内存）

注意：
- 默认 SRS 使用 LOCAL（因为 COLMAP 坐标往往是局部/UTM，并不一定是 ECEF）。
- SensorSize（mm）需要你提供（默认 36mm）。仅凭像素焦距无法可靠推断传感器尺寸。
"""

from __future__ import annotations

import argparse
import os
import random
import xml.etree.ElementTree as ET
from xml.dom import minidom

import numpy as np


def init_root(*, srs_definition: str, srs_name: str, block_name: str, block_description: str) -> ET.Element:
    root = ET.Element("BlocksExchange")
    root.set("version", "3.2")

    spatial_reference_systems = ET.SubElement(root, "SpatialReferenceSystems")

    srs_wgs84 = ET.SubElement(spatial_reference_systems, "SRS")
    ET.SubElement(srs_wgs84, "Id").text = "1"
    ET.SubElement(srs_wgs84, "Name").text = "WGS 84 (EPSG:4326)"
    ET.SubElement(srs_wgs84, "Definition").text = "WGS84"

    srs_custom = ET.SubElement(spatial_reference_systems, "SRS")
    ET.SubElement(srs_custom, "Id").text = "2"
    ET.SubElement(srs_custom, "Name").text = srs_name
    ET.SubElement(srs_custom, "Definition").text = srs_definition

    block = ET.SubElement(root, "Block")
    ET.SubElement(block, "Name").text = block_name
    ET.SubElement(block, "Description").text = block_description
    ET.SubElement(block, "SRSId").text = "2"

    ET.SubElement(block, "Photogroups")
    ET.SubElement(block, "TiePoints")

    return root


def add_photogroup(_root: ET.Element, cam_data: dict, phg_name: str, *, camera_orientation: str) -> None:
    photogroups = _root.find("Block").find("Photogroups")
    photogroup = ET.SubElement(photogroups, "Photogroup")
    ET.SubElement(photogroup, "Name").text = phg_name
    ET.SubElement(photogroup, "ManualOpticalParams").text = "true"
    ET.SubElement(photogroup, "ManualPose").text = "true"

    imagedim = ET.SubElement(photogroup, "ImageDimensions")
    ET.SubElement(imagedim, "Width").text = str(cam_data["width"])
    ET.SubElement(imagedim, "Height").text = str(cam_data["height"])

    ET.SubElement(photogroup, "CameraModelType").text = "Perspective"
    ET.SubElement(photogroup, "CameraModelBand").text = "Visible"
    ET.SubElement(photogroup, "FocalLengthPixels").text = str(cam_data["focal"])
    ET.SubElement(photogroup, "SensorSize").text = str(cam_data["sensor_size"])
    ET.SubElement(photogroup, "CameraOrientation").text = camera_orientation

    principal = ET.SubElement(photogroup, "PrincipalPoint")
    ET.SubElement(principal, "x").text = str(cam_data.get("cx", cam_data["width"] / 2.0))
    ET.SubElement(principal, "y").text = str(cam_data.get("cy", cam_data["height"] / 2.0))

    dist = ET.SubElement(photogroup, "Distortion")
    ET.SubElement(dist, "K1").text = str(cam_data.get("k1", 0.0))
    ET.SubElement(dist, "K2").text = str(cam_data.get("k2", 0.0))
    ET.SubElement(dist, "K3").text = str(cam_data.get("k3", 0.0))
    ET.SubElement(dist, "P1").text = str(cam_data.get("p1", 0.0))
    ET.SubElement(dist, "P2").text = str(cam_data.get("p2", 0.0))

    ET.SubElement(photogroup, "AspectRatio").text = "1"
    ET.SubElement(photogroup, "Skew").text = "0"


def add_photo(_root: ET.Element, image_data: dict, photogroup_name: str, image_dir: str) -> None:
    photogroups = _root.find("Block").find("Photogroups")
    photogroup = None
    for pg in photogroups.findall("Photogroup"):
        if pg.find("Name").text == photogroup_name:
            photogroup = pg
            break
    if photogroup is None:
        raise RuntimeError(f"Photogroup {photogroup_name} not found")

    photo = ET.SubElement(photogroup, "Photo")
    ET.SubElement(photo, "Id").text = str(image_data["Id"])
    if image_dir:
        ET.SubElement(photo, "ImagePath").text = os.path.join(image_dir, image_data["Name"])
    else:
        ET.SubElement(photo, "ImagePath").text = image_data["Name"]
    ET.SubElement(photo, "Component").text = "1"

    pose = ET.SubElement(photo, "Pose")
    rotation = ET.SubElement(pose, "Rotation")

    Rm = image_data["Rotation_mat"]
    for i in range(3):
        for j in range(3):
            ET.SubElement(rotation, f"M_{i}{j}").text = str(float(Rm[i, j]))
    ET.SubElement(rotation, "Accurate").text = "true"

    center = ET.SubElement(pose, "Center")
    ET.SubElement(center, "x").text = str(float(image_data["Center"]["x"]))
    ET.SubElement(center, "y").text = str(float(image_data["Center"]["y"]))
    ET.SubElement(center, "z").text = str(float(image_data["Center"]["z"]))
    ET.SubElement(center, "Accurate").text = "true"


def add_tiepoint(_root: ET.Element, pt: dict) -> None:
    tiepoints = _root.find("Block").find("TiePoints")
    tp = ET.SubElement(tiepoints, "TiePoint")

    pos = ET.SubElement(tp, "Position")
    ET.SubElement(pos, "x").text = str(pt["Position"]["x"])
    ET.SubElement(pos, "y").text = str(pt["Position"]["y"])
    ET.SubElement(pos, "z").text = str(pt["Position"]["z"])

    color = ET.SubElement(tp, "Color")
    ET.SubElement(color, "Red").text = str(pt["Color"]["Red"])
    ET.SubElement(color, "Green").text = str(pt["Color"]["Green"])
    ET.SubElement(color, "Blue").text = str(pt["Color"]["Blue"])

    for m in pt["Measurement"]:
        meas = ET.SubElement(tp, "Measurement")
        ET.SubElement(meas, "PhotoId").text = str(m["PhotoId"])
        ET.SubElement(meas, "x").text = str(m["x"])
        ET.SubElement(meas, "y").text = str(m["y"])


def pretty_write(root: ET.Element, path: str) -> None:
    xmlstr = minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(indent="\t")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xmlstr)


def qvec2rotmat(qvec: np.ndarray) -> np.ndarray:
    """COLMAP qvec (qw, qx, qy, qz) -> rotation matrix (world->camera)."""
    qw, qx, qy, qz = qvec.tolist()
    return np.array(
        [
            [1 - 2 * qy * qy - 2 * qz * qz, 2 * qx * qy - 2 * qw * qz, 2 * qx * qz + 2 * qw * qy],
            [2 * qx * qy + 2 * qw * qz, 1 - 2 * qx * qx - 2 * qz * qz, 2 * qy * qz - 2 * qw * qx],
            [2 * qx * qz - 2 * qw * qy, 2 * qy * qz + 2 * qw * qx, 1 - 2 * qx * qx - 2 * qy * qy],
        ],
        dtype=float,
    )


def parse_srs(s: str) -> tuple[str, str]:
    s = (s or "").strip()
    if not s or s.upper() == "LOCAL":
        return ("LOCAL", "Local coordinate system")
    if s.upper().startswith("EPSG:"):
        s = s.upper()
        return (s, f"SRS ({s})")
    if s.isdigit():
        return (f"EPSG:{s}", f"SRS (EPSG:{s})")
    return (s, f"SRS ({s})")


def parse_cameras_txt(cameras_txt_path: str, *, sensor_size_mm: float) -> dict[str, dict]:
    cameras_data: dict[str, dict] = {}
    with open(cameras_txt_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() == "" or line[0] == "#":
                continue
            parts = line.strip().split()
            cid = parts[0]
            model = parts[1]
            width = int(parts[2])
            height = int(parts[3])

            if model.upper().startswith("OPENCV"):
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
                cam = {
                    "id": cid,
                    "model": model,
                    "width": width,
                    "height": height,
                    "fx": fx,
                    "fy": fy,
                    "cx": cx,
                    "cy": cy,
                    "focal": focal,
                    "k1": k1,
                    "k2": k2,
                    "p1": p1,
                    "p2": p2,
                    "k3": k3,
                }
            elif model.upper() == "SIMPLE_RADIAL":
                focal = float(parts[4])
                cx = float(parts[5])
                cy = float(parts[6])
                k1 = float(parts[7]) if len(parts) > 7 else 0.0
                cam = {
                    "id": cid,
                    "model": model,
                    "width": width,
                    "height": height,
                    "fx": focal,
                    "fy": focal,
                    "cx": cx,
                    "cy": cy,
                    "focal": focal,
                    "k1": k1,
                    "k2": 0.0,
                    "p1": 0.0,
                    "p2": 0.0,
                    "k3": 0.0,
                }
            elif model.upper() == "RADIAL":
                focal = float(parts[4])
                cx = float(parts[5])
                cy = float(parts[6])
                k1 = float(parts[7]) if len(parts) > 7 else 0.0
                k2 = float(parts[8]) if len(parts) > 8 else 0.0
                cam = {
                    "id": cid,
                    "model": model,
                    "width": width,
                    "height": height,
                    "fx": focal,
                    "fy": focal,
                    "cx": cx,
                    "cy": cy,
                    "focal": focal,
                    "k1": k1,
                    "k2": k2,
                    "p1": 0.0,
                    "p2": 0.0,
                    "k3": 0.0,
                }
            elif model.upper() == "PINHOLE":
                fx = float(parts[4])
                fy = float(parts[5])
                cx = float(parts[6])
                cy = float(parts[7])
                focal = (fx + fy) / 2.0
                cam = {
                    "id": cid,
                    "model": model,
                    "width": width,
                    "height": height,
                    "fx": fx,
                    "fy": fy,
                    "cx": cx,
                    "cy": cy,
                    "focal": focal,
                    "k1": 0.0,
                    "k2": 0.0,
                    "p1": 0.0,
                    "p2": 0.0,
                    "k3": 0.0,
                }
            else:
                focal = float(parts[4])
                cx = float(parts[5]) if len(parts) > 5 else width / 2.0
                cy = float(parts[6]) if len(parts) > 6 else height / 2.0
                cam = {
                    "id": cid,
                    "model": model,
                    "width": width,
                    "height": height,
                    "fx": focal,
                    "fy": focal,
                    "cx": cx,
                    "cy": cy,
                    "focal": focal,
                    "k1": 0.0,
                    "k2": 0.0,
                    "p1": 0.0,
                    "p2": 0.0,
                    "k3": 0.0,
                }

            cam["sensor_size"] = float(sensor_size_mm)
            cameras_data[cid] = cam

    return cameras_data


def reservoir_sample_points3d(
    points3d_txt_path: str, *, max_tiepoints: int, min_track_length: int, seed: int
) -> dict[int, dict]:
    """
    Read points3D.txt and return selected points dict {pid -> point_dict}.
    max_tiepoints:
      - 0  => none
      - -1 => all (⚠️ huge XML)
      - >0 => sample via reservoir sampling
    """
    if max_tiepoints == 0:
        return {}

    rng = random.Random(seed)
    reservoir: list[dict] = []
    seen = 0

    with open(points3d_txt_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() == "" or line[0] == "#":
                continue
            parts = line.strip().split()
            pid = int(parts[0])
            xw = float(parts[1])
            yw = float(parts[2])
            zw = float(parts[3])
            r = int(parts[4])
            g = int(parts[5])
            b = int(parts[6])

            track_len = max(0, (len(parts) - 8) // 2)
            if track_len < min_track_length:
                continue

            point = {
                "id": pid,
                "Position": {"x": xw, "y": yw, "z": zw},
                "Color": {"Red": r / 255.0, "Green": g / 255.0, "Blue": b / 255.0},
                "Measurement": [],
            }

            if max_tiepoints < 0:
                reservoir.append(point)
                continue

            seen += 1
            if len(reservoir) < max_tiepoints:
                reservoir.append(point)
            else:
                j = rng.randrange(seen)
                if j < max_tiepoints:
                    reservoir[j] = point

    return {p["id"]: p for p in reservoir}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert COLMAP text model (cameras.txt/images.txt/points3D.txt) to ContextCapture BlocksExchange XML."
    )
    parser.add_argument("colmap_dir", help="Directory containing cameras.txt/images.txt/points3D.txt")
    parser.add_argument(
        "--image-dir",
        default="",
        help="Image directory used to build <ImagePath>. Default: write just the filename.",
    )
    parser.add_argument("--output", default="", help="Output XML path. Default: <colmap_dir>/block_opensfm.xml")
    parser.add_argument(
        "--sensor-size-mm",
        type=float,
        default=36.0,
        help="Sensor size (mm) written to CC <SensorSize>. Default: 36.0",
    )
    parser.add_argument("--srs", default="LOCAL", help="SRS definition: LOCAL (default), EPSG:xxxx, or 'xxxx'")
    parser.add_argument("--block-name", default="COLMAP - AT", help="BlocksExchange <Block><Name>")
    parser.add_argument("--block-description", default="COLMAP converts to CC", help="BlocksExchange <Block><Description>")
    parser.add_argument("--camera-orientation", default="XRightYUp", help="CC <CameraOrientation>. Default: XRightYUp")
    parser.add_argument("--max-tiepoints", type=int, default=0, help="0=none (default), -1=all (⚠️ huge), >0=sample N")
    parser.add_argument("--min-track-length", type=int, default=2, help="Minimum track length for exported tiepoints. Default: 2")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for tiepoint sampling. Default: 0")
    args = parser.parse_args()

    directory_colmap = args.colmap_dir
    cameras_txt_path = os.path.join(directory_colmap, "cameras.txt")
    images_txt_path = os.path.join(directory_colmap, "images.txt")
    points3d_txt_path = os.path.join(directory_colmap, "points3D.txt")
    output_xml_path = args.output or os.path.join(directory_colmap, "block_opensfm.xml")

    if not os.path.exists(cameras_txt_path) or not os.path.exists(images_txt_path):
        raise FileNotFoundError("Missing cameras.txt/images.txt in colmap_dir")

    cameras_data = parse_cameras_txt(cameras_txt_path, sensor_size_mm=args.sensor_size_mm)

    points3d_data: dict[int, dict] = {}
    if args.max_tiepoints != 0:
        if not os.path.exists(points3d_txt_path):
            raise FileNotFoundError("points3D.txt not found but --max-tiepoints != 0")
        points3d_data = reservoir_sample_points3d(
            points3d_txt_path, max_tiepoints=args.max_tiepoints, min_track_length=args.min_track_length, seed=args.seed
        )
    wanted_pids = set(points3d_data.keys())

    images_data: dict[int, dict] = {}
    flag_odd = True
    current_header: dict | None = None
    with open(images_txt_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() == "" or line[0] == "#":
                continue
            if flag_odd:
                parts = line.strip().split()
                img_id = int(parts[0])
                qw = float(parts[1])
                qx = float(parts[2])
                qy = float(parts[3])
                qz = float(parts[4])
                tx = float(parts[5])
                ty = float(parts[6])
                tz = float(parts[7])
                cam_id = parts[8]
                name = parts[9]
                current_header = {
                    "Id": img_id,
                    "quat": np.array([qw, qx, qy, qz], dtype=float),
                    "t_wc": np.array([tx, ty, tz], dtype=float),
                    "Camera": cam_id,
                    "Name": name,
                }
                flag_odd = False
            else:
                # POINTS2D triples (x, y, point3D_id)
                if wanted_pids and current_header is not None:
                    parts = line.strip().split()
                    img_id = current_header["Id"]
                    for i in range(0, len(parts), 3):
                        if i + 2 >= len(parts):
                            break
                        pid = int(parts[i + 2])
                        if pid != -1 and pid in wanted_pids:
                            x = float(parts[i])
                            y = float(parts[i + 1])
                            points3d_data[pid]["Measurement"].append({"PhotoId": img_id, "x": x, "y": y})

                if current_header is not None:
                    images_data[current_header["Id"]] = current_header
                current_header = None
                flag_odd = True

    srs_def, srs_name = parse_srs(args.srs)
    root = init_root(
        srs_definition=srs_def,
        srs_name=srs_name,
        block_name=args.block_name,
        block_description=args.block_description,
    )

    cam_to_phg: dict[str, str] = {}
    for i, (cam_name, cam) in enumerate(cameras_data.items()):
        phg_name = f"Photogroup {i + 1}"
        cam_to_phg[cam_name] = phg_name
        add_photogroup(root, cam, phg_name, camera_orientation=args.camera_orientation)

    # axis transform matrix S: COLMAP camera axes (x right, y down, z forward)
    # -> CC (commonly x right, y up, z backward) for CameraOrientation=XRightYUp
    S = np.diag([1.0, -1.0, -1.0])

    for img in images_data.values():
        qvec = img["quat"]
        R_wc = qvec2rotmat(qvec)  # world -> camera (COLMAP)
        R_cw_colmap = R_wc.T      # camera -> world
        t_wc = img["t_wc"]

        C_world = -R_cw_colmap @ t_wc
        R_cw_cc = R_cw_colmap @ S

        img["Rotation_mat"] = R_cw_cc
        img["Center"] = {"x": float(C_world[0]), "y": float(C_world[1]), "z": float(C_world[2])}
        add_photo(root, img, cam_to_phg[img["Camera"]], args.image_dir)

    exported_tp = 0
    if points3d_data:
        for pt in points3d_data.values():
            if len(pt.get("Measurement", [])) >= args.min_track_length:
                add_tiepoint(root, pt)
                exported_tp += 1

    pretty_write(root, output_xml_path)

    print(f"Successfully converted {len(images_data)} images to CC format")
    if args.max_tiepoints != 0:
        print(f"Exported {exported_tp} tiepoints (requested max_tiepoints={args.max_tiepoints})")
    print(f"Output saved to: {output_xml_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





