"""Reader for COLMAP/GLOMAP reconstruction results."""
import os
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..schemas import CameraInfo, Point3D


class ResultReader:
    """Reader for COLMAP binary format reconstruction files."""
    
    @staticmethod
    def read_cameras(output_path: str) -> List[CameraInfo]:
        """Read camera poses from reconstruction.
        
        同时兼容 COLMAP/InstantSFM 的 `images.bin` 与 `images.txt` 文本格式。
        
        Args:
            output_path: Path to output directory
            
        Returns:
            List of CameraInfo
        """
        # Find the sparse reconstruction directory
        sparse_dir = ResultReader._find_sparse_dir(output_path)
        if not sparse_dir:
            raise FileNotFoundError("No sparse reconstruction found")
        
        images_bin = os.path.join(sparse_dir, "images.bin")
        images_txt = os.path.join(sparse_dir, "images.txt")
        
        if os.path.exists(images_bin):
            return ResultReader._read_cameras_bin(images_bin)
        elif os.path.exists(images_txt):
            return ResultReader._read_cameras_txt(images_txt)
        else:
            raise FileNotFoundError("Neither images.bin nor images.txt found")
    
    @staticmethod
    def read_points3d(output_path: str, limit: int = 100000) -> Tuple[List[Dict[str, Any]], int]:
        """Read 3D points from reconstruction with stride sampling to maintain overall shape.
        
        同时兼容 COLMAP/InstantSFM 的 `points3D.bin` 与 `points3D.txt` 文本格式。
        
        Args:
            output_path: Path to output directory
            limit: Maximum number of points to return
            
        Returns:
            Tuple of (sampled points list, total number of points in file)
        """
        sparse_dir = ResultReader._find_sparse_dir(output_path)
        if not sparse_dir:
            raise FileNotFoundError("No sparse reconstruction found")
        
        points_bin = os.path.join(sparse_dir, "points3D.bin")
        points_txt = os.path.join(sparse_dir, "points3D.txt")
        
        if os.path.exists(points_bin):
            return ResultReader._read_points3d_bin(points_bin, limit)
        elif os.path.exists(points_txt):
            return ResultReader._read_points3d_txt(points_txt, limit)
        else:
            raise FileNotFoundError("Neither points3D.bin nor points3D.txt found")
    
    @staticmethod
    def get_stats(output_path: str) -> Dict[str, Any]:
        """Get reconstruction statistics.
        
        同时兼容二进制与文本格式输出。
        
        Args:
            output_path: Path to output directory
            
        Returns:
            Statistics dictionary
        """
        sparse_dir = ResultReader._find_sparse_dir(output_path)
        if not sparse_dir:
            return {}
        
        stats = {
            "num_images": 0,
            "num_registered_images": 0,
            "num_points3d": 0,
            "num_observations": 0,
            "mean_reprojection_error": 0.0,
            "mean_track_length": 0.0,
        }
        
        # Count registered images
        images_bin = os.path.join(sparse_dir, "images.bin")
        images_txt = os.path.join(sparse_dir, "images.txt")
        if os.path.exists(images_bin):
            with open(images_bin, "rb") as f:
                stats["num_registered_images"] = struct.unpack("<Q", f.read(8))[0]
                stats["num_images"] = stats["num_registered_images"]
        elif os.path.exists(images_txt):
            # 统计 images.txt 中的有效相机行（非注释行的第一行）
            with open(images_txt, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            count = 0
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith("#"):
                    i += 1
                    continue
                # 把这一行当作一个已注册图像的记录
                count += 1
                # 跳过下一行的 2D-3D 观测（如果存在）
                if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                    i += 2
                else:
                    i += 1
            stats["num_registered_images"] = count
            stats["num_images"] = count
        
        # Count 3D points and compute stats
        points_bin = os.path.join(sparse_dir, "points3D.bin")
        points_txt = os.path.join(sparse_dir, "points3D.txt")
        if os.path.exists(points_bin):
            total_error = 0.0
            total_track_length = 0
            
            with open(points_bin, "rb") as f:
                num_points = struct.unpack("<Q", f.read(8))[0]
                stats["num_points3d"] = num_points
                
                for _ in range(num_points):
                    # Skip point_id, xyz, rgb
                    f.read(8 + 24 + 3)
                    error = struct.unpack("<d", f.read(8))[0]
                    track_length = struct.unpack("<Q", f.read(8))[0]
                    f.read(track_length * 8)  # Skip track
                    
                    total_error += error
                    total_track_length += track_length
                    stats["num_observations"] += track_length
            
            if num_points > 0:
                stats["mean_reprojection_error"] = total_error / num_points
                stats["mean_track_length"] = total_track_length / num_points
        elif os.path.exists(points_txt):
            total_error = 0.0
            total_track_length = 0
            num_points = 0
            
            with open(points_txt, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) < 8:
                        continue
                    
                    num_points += 1
                    error = float(parts[7])
                    
                    track_elems = parts[8:]
                    track_length = max(0, len(track_elems) // 2)
                    
                    total_error += error
                    total_track_length += track_length
                    stats["num_observations"] += track_length
            
            stats["num_points3d"] = num_points
            if num_points > 0:
                stats["mean_reprojection_error"] = total_error / num_points
                stats["mean_track_length"] = total_track_length / num_points
        
        return stats
    
    @staticmethod
    def _find_sparse_dir(output_path: str) -> Optional[str]:
        """Find the sparse reconstruction directory.
        
        COLMAP/GLOMAP may create numbered subdirectories (0, 1, ...)
        
        Args:
            output_path: Base output path
            
        Returns:
            Path to sparse directory or None
        """
        # Check common locations
        candidates = [
            os.path.join(output_path, "sparse", "0"),
            os.path.join(output_path, "sparse"),
            os.path.join(output_path, "0"),
            output_path,
        ]
        
        for path in candidates:
            if (
                os.path.exists(os.path.join(path, "images.bin"))
                or os.path.exists(os.path.join(path, "images.txt"))
            ):
                return path
        
        return None

    # ------------------------------------------------------------------
    # Internal helpers for different formats
    # ------------------------------------------------------------------
    @staticmethod
    def _read_cameras_bin(images_bin: str) -> List[CameraInfo]:
        """读取 COLMAP 二进制 `images.bin`。"""
        cameras: List[CameraInfo] = []
        
        with open(images_bin, "rb") as f:
            num_images = struct.unpack("<Q", f.read(8))[0]
            
            for _ in range(num_images):
                # Read image data
                image_id = struct.unpack("<I", f.read(4))[0]
                qw, qx, qy, qz = struct.unpack("<4d", f.read(32))
                tx, ty, tz = struct.unpack("<3d", f.read(24))
                camera_id = struct.unpack("<I", f.read(4))[0]
                
                # Read image name (null-terminated string)
                name_chars = []
                while True:
                    char = f.read(1)
                    if char == b"\x00":
                        break
                    name_chars.append(char.decode("utf-8"))
                image_name = "".join(name_chars)
                
                # Read 2D points
                num_points2d = struct.unpack("<Q", f.read(8))[0]
                # Skip point data (x, y, point3d_id for each)
                f.read(num_points2d * 24)  # 8 + 8 + 8 bytes per point
                
                # Count valid 3D observations
                num_points = 0  # TODO: 如果需要精确数量，可以在这里解析 point3d_id
                
                cameras.append(
                    CameraInfo(
                        image_id=image_id,
                        image_name=image_name,
                        camera_id=camera_id,
                        qw=qw,
                        qx=qx,
                        qy=qy,
                        qz=qz,
                        tx=tx,
                        ty=ty,
                        tz=tz,
                        num_points=num_points,
                    )
                )
        
        return cameras

    @staticmethod
    def _read_cameras_txt(images_txt: str) -> List[CameraInfo]:
        """读取 COLMAP/InstantSFM 文本格式 `images.txt`。
        
        该格式通常为：
        IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME
        x1 y1 POINT3D_ID1 x2 y2 POINT3D_ID2 ...
        """
        cameras: List[CameraInfo] = []
        
        with open(images_txt, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("#"):
                i += 1
                continue
            
            # 第一行：姿态 + 相机 ID + 图片名
            parts = line.split()
            if len(parts) < 10:
                # 格式异常，跳过
                i += 1
                continue
            
            image_id = int(parts[0])
            qw, qx, qy, qz = map(float, parts[1:5])
            tx, ty, tz = map(float, parts[5:8])
            camera_id = int(parts[8])
            image_name = " ".join(parts[9:])
            
            # 下一行是 2D-3D 对应点
            num_points = 0
            if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                obs_parts = lines[i + 1].split()
                # 每个观测是 (x, y, point3d_id) 三元组
                for j in range(2, len(obs_parts), 3):
                    try:
                        point3d_id = int(obs_parts[j])
                        if point3d_id != -1:
                            num_points += 1
                    except (ValueError, IndexError):
                        continue
                i += 2
            else:
                i += 1
            
            cameras.append(
                CameraInfo(
                    image_id=image_id,
                    image_name=image_name,
                    camera_id=camera_id,
                    qw=qw,
                    qx=qx,
                    qy=qy,
                    qz=qz,
                    tx=tx,
                    ty=ty,
                    tz=tz,
                    num_points=num_points,
                )
            )
        
        return cameras

    @staticmethod
    def _read_points3d_bin(points_bin: str, limit: int) -> Tuple[List[Dict[str, Any]], int]:
        """读取 COLMAP 二进制 `points3D.bin`。"""
        points: List[Dict[str, Any]] = []
        
        with open(points_bin, "rb") as f:
            num_points = struct.unpack("<Q", f.read(8))[0]
            
            # Calculate stride for uniform sampling
            # If num_points <= limit, stride=1 (return all points)
            # Otherwise, sample uniformly to maintain overall shape
            stride = max(1, num_points // limit) if num_points > limit else 1
            
            for i in range(num_points):
                # Read point data (must read completely to maintain file pointer)
                point_id = struct.unpack("<Q", f.read(8))[0]
                x, y, z = struct.unpack("<3d", f.read(24))
                r, g, b = struct.unpack("<3B", f.read(3))
                error = struct.unpack("<d", f.read(8))[0]
                
                # Read track (observations)
                track_length = struct.unpack("<Q", f.read(8))[0]
                # Skip track data (image_id, point2d_idx for each)
                f.read(track_length * 8)  # 4 + 4 bytes per observation
                
                # Only keep points that match stride sampling
                if i % stride == 0:
                    points.append(
                        {
                            "id": point_id,
                            "x": x,
                            "y": y,
                            "z": z,
                            "r": r,
                            "g": g,
                            "b": b,
                            "error": error,
                            "num_observations": track_length,
                        }
                    )
        
        # Safety check: if sampling still exceeds limit, truncate
        # (theoretically shouldn't happen, but just in case)
        if len(points) > limit:
            points = points[:limit]
        
        return points, num_points

    @staticmethod
    def _read_points3d_txt(points_txt: str, limit: int) -> Tuple[List[Dict[str, Any]], int]:
        """读取 COLMAP/InstantSFM 文本格式 `points3D.txt`。
        
        该格式通常为：
        POINT3D_ID X Y Z R G B ERROR TRACK[]
        其中 TRACK 是若干 (image_id, point2d_idx) 对。
        """
        # 先把所有非注释行读入内存，以便计算总点数并做 stride 采样
        with open(points_txt, "r", encoding="utf-8") as f:
            pure_lines = [ln.strip() for ln in f.readlines() if ln.strip() and not ln.lstrip().startswith("#")]
        
        num_points = len(pure_lines)
        if num_points == 0:
            return [], 0
        
        stride = max(1, num_points // limit) if num_points > limit else 1
        
        points: List[Dict[str, Any]] = []
        for idx, line in enumerate(pure_lines):
            parts = line.split()
            if len(parts) < 8:
                continue
            
            point_id = int(parts[0])
            x, y, z = map(float, parts[1:4])
            r, g, b = map(int, parts[4:7])
            error = float(parts[7])
            
            # 后面是 track: image_id, point2d_idx 成对出现
            track_elems = parts[8:]
            track_length = max(0, len(track_elems) // 2)
            
            if idx % stride == 0:
                points.append(
                    {
                        "id": point_id,
                        "x": x,
                        "y": y,
                        "z": z,
                        "r": r,
                        "g": g,
                        "b": b,
                        "error": error,
                        "num_observations": track_length,
                    }
                )
        
        if len(points) > limit:
            points = points[:limit]
        
        return points, num_points
