"""Reader for COLMAP/GLOMAP reconstruction results."""
import os
import struct
import json
import math
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

        # InstantSfM may export points3D.txt with ERROR column always 0.0.
        # If so, compute mean reprojection error from 2D observations in images.txt.
        try:
            if stats.get("mean_reprojection_error", 0.0) == 0.0:
                images_txt = os.path.join(sparse_dir, "images.txt")
                cameras_txt = os.path.join(sparse_dir, "cameras.txt")
                points_txt = os.path.join(sparse_dir, "points3D.txt")
                if os.path.exists(images_txt) and os.path.exists(cameras_txt) and os.path.exists(points_txt):
                    computed = ResultReader._compute_mean_reprojection_error_with_cache(
                        sparse_dir=sparse_dir,
                        cameras_txt=cameras_txt,
                        images_txt=images_txt,
                        points3d_txt=points_txt,
                    )
                    if computed and computed.get("mean_reprojection_error", 0.0) > 0.0:
                        stats["mean_reprojection_error"] = float(computed["mean_reprojection_error"])
                        # Prefer computed observation count (more accurate than track_length in some exports)
                        if computed.get("num_observations") is not None:
                            stats["num_observations"] = int(computed["num_observations"])
        except Exception:
            # Never fail stats due to reprojection computation
            pass

        # For merged partition results we often only have binary files (cameras.bin/images.bin/points3D.bin),
        # and InstantSfM points may have ERROR=0 so we cannot recompute reprojection error from observations.
        # Allow a lightweight override produced during merge.
        try:
            if stats.get("mean_reprojection_error", 0.0) == 0.0:
                merged_stats_path = os.path.join(sparse_dir, "merged_stats.json")
                if os.path.exists(merged_stats_path):
                    with open(merged_stats_path, "r", encoding="utf-8") as f:
                        ms = json.load(f) or {}
                    m_err = float(ms.get("mean_reprojection_error", 0.0) or 0.0)
                    if m_err > 0.0:
                        stats["mean_reprojection_error"] = m_err
                    # Optional overrides for completeness
                    if ms.get("num_observations") is not None:
                        stats["num_observations"] = int(ms["num_observations"])
                    if ms.get("mean_track_length") is not None:
                        stats["mean_track_length"] = float(ms["mean_track_length"])
        except Exception:
            pass
        
        return stats
    
    @staticmethod
    def _find_sparse_dir(output_path: str) -> Optional[str]:
        """Find the sparse reconstruction directory.
        
        For partitioned SfM, prioritizes merged/sparse/0 over sparse/0.
        COLMAP/GLOMAP may create numbered subdirectories (0, 1, ...)
        
        Args:
            output_path: Base output path
            
        Returns:
            Path to sparse directory or None
        """
        # Check common locations (prioritize merged results for partitioned SfM)
        candidates = [
            os.path.join(output_path, "merged", "sparse", "0"),  # Partitioned merge result
            os.path.join(output_path, "sparse", "0"),  # Regular or symlinked result
            os.path.join(output_path, "sparse"),  # Fallback
            os.path.join(output_path, "0"),  # Alternative layout
            output_path,  # Direct output
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
    
    # ------------------------------------------------------------------
    # Partition-specific methods
    # ------------------------------------------------------------------
    @staticmethod
    def read_partition_cameras(output_path: str, partition_index: int) -> List[CameraInfo]:
        """Read camera poses from a specific partition.
        
        同时兼容 COLMAP/InstantSFM 的 `images.bin` 与 `images.txt` 文本格式。
        
        Args:
            output_path: Base output path
            partition_index: Partition index
            
        Returns:
            List of CameraInfo
        """
        partition_sparse = os.path.join(
            output_path,
            "partitions",
            f"partition_{partition_index}",
            "sparse",
            "0",
        )
        
        if not os.path.exists(partition_sparse):
            raise FileNotFoundError(f"Partition {partition_index} sparse directory not found")
        
        images_bin = os.path.join(partition_sparse, "images.bin")
        images_txt = os.path.join(partition_sparse, "images.txt")
        
        if os.path.exists(images_bin):
            return ResultReader._read_cameras_bin(images_bin)
        elif os.path.exists(images_txt):
            return ResultReader._read_cameras_txt(images_txt)
        else:
            raise FileNotFoundError(f"Partition {partition_index}: Neither images.bin nor images.txt found")
    
    @staticmethod
    def read_partition_points3d(
        output_path: str, 
        partition_index: int, 
        limit: int = 100000
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Read 3D points from a specific partition.
        
        同时兼容 COLMAP/InstantSFM 的 `points3D.bin` 与 `points3D.txt` 文本格式。
        
        Args:
            output_path: Base output path
            partition_index: Partition index
            limit: Maximum number of points to return
            
        Returns:
            Tuple of (sampled points list, total number of points in file)
        """
        partition_sparse = os.path.join(
            output_path,
            "partitions",
            f"partition_{partition_index}",
            "sparse",
            "0",
        )
        
        if not os.path.exists(partition_sparse):
            raise FileNotFoundError(f"Partition {partition_index} sparse directory not found")
        
        points_bin = os.path.join(partition_sparse, "points3D.bin")
        points_txt = os.path.join(partition_sparse, "points3D.txt")
        
        if os.path.exists(points_bin):
            return ResultReader._read_points3d_bin(points_bin, limit)
        elif os.path.exists(points_txt):
            return ResultReader._read_points3d_txt(points_txt, limit)
        else:
            raise FileNotFoundError(f"Partition {partition_index}: Neither points3D.bin nor points3D.txt found")
    
    @staticmethod
    def read_partition_stats(output_path: str, partition_index: int) -> Dict[str, Any]:
        """Get reconstruction statistics for a specific partition.
        
        同时兼容二进制与文本格式输出。
        
        Args:
            output_path: Base output path
            partition_index: Partition index
            
        Returns:
            Statistics dictionary
        """
        partition_sparse = os.path.join(
            output_path,
            "partitions",
            f"partition_{partition_index}",
            "sparse",
            "0",
        )
        
        if not os.path.exists(partition_sparse):
            return {}
        
        return ResultReader.get_stats(partition_sparse)

    # ------------------------------------------------------------------
    # Reprojection error computation (for exports with zero ERROR column)
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_mean_reprojection_error_with_cache(
        sparse_dir: str,
        cameras_txt: str,
        images_txt: str,
        points3d_txt: str,
    ) -> Optional[Dict[str, Any]]:
        """Compute mean reprojection error (px) from images.txt observations with local cache.

        Cache file is stored inside sparse_dir and keyed by input file mtimes/sizes.
        """
        cache_path = os.path.join(sparse_dir, ".reproj_cache.json")

        def _sig(p: str) -> Dict[str, Any]:
            st = os.stat(p)
            return {"path": os.path.basename(p), "mtime": st.st_mtime, "size": st.st_size}

        signature = {
            "version": 1,
            "cameras": _sig(cameras_txt),
            "images": _sig(images_txt),
            "points3D": _sig(points3d_txt),
        }

        # Try read cache
        try:
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if cached.get("signature") == signature and "result" in cached:
                    return cached["result"]
        except Exception:
            pass

        # Compute fresh
        result = ResultReader._compute_mean_reprojection_error(
            cameras_txt=cameras_txt,
            images_txt=images_txt,
            points3d_txt=points3d_txt,
        )
        if not result:
            return None

        # Write cache (best-effort)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"signature": signature, "result": result}, f)
        except Exception:
            pass

        return result

    @staticmethod
    def _compute_mean_reprojection_error(
        cameras_txt: str,
        images_txt: str,
        points3d_txt: str,
    ) -> Optional[Dict[str, Any]]:
        """Compute mean reprojection error from (images.txt, cameras.txt, points3D.txt).

        Supports common COLMAP camera models, including OPENCV.
        """
        cameras = ResultReader._parse_cameras_txt(cameras_txt)
        if not cameras:
            return None

        points = ResultReader._parse_points3d_xyz(points3d_txt)
        if not points:
            return None

        total_err = 0.0
        num_obs = 0

        # Stream parse images.txt
        with open(images_txt, "r", encoding="utf-8", errors="replace") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) < 10:
                    continue

                # image pose
                qw, qx, qy, qz = map(float, parts[1:5])
                tx, ty, tz = map(float, parts[5:8])
                cam_id = int(parts[8])

                cam = cameras.get(cam_id)
                if not cam:
                    # Skip observation line
                    _ = f.readline()
                    continue

                R = ResultReader._qvec_to_rotmat(qw, qx, qy, qz)
                t = (tx, ty, tz)

                # Observation line
                obs_line = f.readline()
                if not obs_line:
                    break
                obs_line = obs_line.strip()
                if not obs_line or obs_line.startswith("#"):
                    continue
                obs = obs_line.split()
                # Triples (x, y, point3d_id)
                for j in range(0, len(obs) - 2, 3):
                    try:
                        u = float(obs[j])
                        v = float(obs[j + 1])
                        pid = int(obs[j + 2])
                    except Exception:
                        continue
                    if pid == -1:
                        continue
                    X = points.get(pid)
                    if X is None:
                        continue

                    proj = ResultReader._project_point(cam, R, t, X)
                    if proj is None:
                        continue
                    up, vp = proj
                    du = up - u
                    dv = vp - v
                    total_err += math.hypot(du, dv)
                    num_obs += 1

        if num_obs == 0:
            return None
        return {"mean_reprojection_error": total_err / num_obs, "num_observations": num_obs}

    @staticmethod
    def _parse_cameras_txt(cameras_txt: str) -> Dict[int, Dict[str, Any]]:
        """Parse COLMAP cameras.txt into a dict keyed by camera_id."""
        cams: Dict[int, Dict[str, Any]] = {}
        with open(cameras_txt, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 5:
                    continue
                try:
                    cam_id = int(parts[0])
                    model = parts[1]
                    width = int(parts[2])
                    height = int(parts[3])
                    params = list(map(float, parts[4:]))
                except Exception:
                    continue
                cams[cam_id] = {"model": model, "width": width, "height": height, "params": params}
        return cams

    @staticmethod
    def _parse_points3d_xyz(points3d_txt: str) -> Dict[int, Tuple[float, float, float]]:
        """Parse points3D.txt and return {point3d_id: (x,y,z)}."""
        pts: Dict[int, Tuple[float, float, float]] = {}
        with open(points3d_txt, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue
                try:
                    pid = int(parts[0])
                    x = float(parts[1])
                    y = float(parts[2])
                    z = float(parts[3])
                except Exception:
                    continue
                pts[pid] = (x, y, z)
        return pts

    @staticmethod
    def _qvec_to_rotmat(qw: float, qx: float, qy: float, qz: float) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]:
        """Quaternion (qw,qx,qy,qz) to rotation matrix. (COLMAP qvec is world-to-camera)."""
        # Normalize
        n = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
        if n > 0:
            qw, qx, qy, qz = qw / n, qx / n, qy / n, qz / n

        r00 = 1 - 2 * (qy * qy + qz * qz)
        r01 = 2 * (qx * qy - qz * qw)
        r02 = 2 * (qx * qz + qy * qw)
        r10 = 2 * (qx * qy + qz * qw)
        r11 = 1 - 2 * (qx * qx + qz * qz)
        r12 = 2 * (qy * qz - qx * qw)
        r20 = 2 * (qx * qz - qy * qw)
        r21 = 2 * (qy * qz + qx * qw)
        r22 = 1 - 2 * (qx * qx + qy * qy)
        return ((r00, r01, r02), (r10, r11, r12), (r20, r21, r22))

    @staticmethod
    def _project_point(
        cam: Dict[str, Any],
        R: Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]],
        t: Tuple[float, float, float],
        X: Tuple[float, float, float],
    ) -> Optional[Tuple[float, float]]:
        """Project world point X to pixel using COLMAP camera model and pose (world->cam)."""
        Xw, Yw, Zw = X
        tx, ty, tz = t
        # camera coordinates: Xc = R*X + t
        Xc = R[0][0] * Xw + R[0][1] * Yw + R[0][2] * Zw + tx
        Yc = R[1][0] * Xw + R[1][1] * Yw + R[1][2] * Zw + ty
        Zc = R[2][0] * Xw + R[2][1] * Yw + R[2][2] * Zw + tz
        if Zc <= 1e-12:
            return None

        x = Xc / Zc
        y = Yc / Zc

        model = (cam.get("model") or "").upper()
        p = cam.get("params") or []

        # Distort in normalized coordinates
        if model == "PINHOLE" and len(p) >= 4:
            fx, fy, cx, cy = p[:4]
            xd, yd = x, y
        elif model == "SIMPLE_PINHOLE" and len(p) >= 3:
            f, cx, cy = p[:3]
            fx, fy = f, f
            xd, yd = x, y
        elif model == "SIMPLE_RADIAL" and len(p) >= 4:
            f, cx, cy, k1 = p[:4]
            fx, fy = f, f
            r2 = x * x + y * y
            radial = 1.0 + k1 * r2
            xd, yd = x * radial, y * radial
        elif model == "RADIAL" and len(p) >= 5:
            f, cx, cy, k1, k2 = p[:5]
            fx, fy = f, f
            r2 = x * x + y * y
            radial = 1.0 + k1 * r2 + k2 * r2 * r2
            xd, yd = x * radial, y * radial
        elif model == "OPENCV" and len(p) >= 8:
            fx, fy, cx, cy, k1, k2, p1, p2 = p[:8]
            r2 = x * x + y * y
            radial = 1.0 + k1 * r2 + k2 * r2 * r2
            xrad = x * radial
            yrad = y * radial
            x_tan = 2.0 * p1 * x * y + p2 * (r2 + 2.0 * x * x)
            y_tan = p1 * (r2 + 2.0 * y * y) + 2.0 * p2 * x * y
            xd = xrad + x_tan
            yd = yrad + y_tan
        elif model == "OPENCV5" and len(p) >= 9:
            fx, fy, cx, cy, k1, k2, p1, p2, k3 = p[:9]
            r2 = x * x + y * y
            radial = 1.0 + k1 * r2 + k2 * r2 * r2 + k3 * r2 * r2 * r2
            xrad = x * radial
            yrad = y * radial
            x_tan = 2.0 * p1 * x * y + p2 * (r2 + 2.0 * x * x)
            y_tan = p1 * (r2 + 2.0 * y * y) + 2.0 * p2 * x * y
            xd = xrad + x_tan
            yd = yrad + y_tan
        else:
            # Unknown/unsupported model -> fall back to pinhole if possible
            if len(p) >= 4:
                fx, fy, cx, cy = p[:4]
                xd, yd = x, y
            elif len(p) >= 3:
                f, cx, cy = p[:3]
                fx, fy = f, f
                xd, yd = x, y
            else:
                return None

        u = fx * xd + cx
        v = fy * yd + cy
        return u, v