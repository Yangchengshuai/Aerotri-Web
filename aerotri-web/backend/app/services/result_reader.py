"""Reader for COLMAP/GLOMAP reconstruction results."""
import os
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..schemas import CameraInfo, Point3D


class ResultReader:
    """Reader for COLMAP binary format reconstruction files."""
    
    @staticmethod
    def read_cameras(output_path: str) -> List[CameraInfo]:
        """Read camera poses from reconstruction.
        
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
        if not os.path.exists(images_bin):
            raise FileNotFoundError("images.bin not found")
        
        cameras = []
        
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
                    if char == b'\x00':
                        break
                    name_chars.append(char.decode('utf-8'))
                image_name = ''.join(name_chars)
                
                # Read 2D points
                num_points2d = struct.unpack("<Q", f.read(8))[0]
                # Skip point data (x, y, point3d_id for each)
                f.read(num_points2d * 24)  # 8 + 8 + 8 bytes per point
                
                # Count valid 3D observations
                num_points = 0  # Would need to track point3d_ids
                
                cameras.append(CameraInfo(
                    image_id=image_id,
                    image_name=image_name,
                    camera_id=camera_id,
                    qw=qw, qx=qx, qy=qy, qz=qz,
                    tx=tx, ty=ty, tz=tz,
                    num_points=num_points
                ))
        
        return cameras
    
    @staticmethod
    def read_points3d(output_path: str, limit: int = 100000) -> List[Dict[str, Any]]:
        """Read 3D points from reconstruction.
        
        Args:
            output_path: Path to output directory
            limit: Maximum number of points to read
            
        Returns:
            List of point dictionaries
        """
        sparse_dir = ResultReader._find_sparse_dir(output_path)
        if not sparse_dir:
            raise FileNotFoundError("No sparse reconstruction found")
        
        points_bin = os.path.join(sparse_dir, "points3D.bin")
        if not os.path.exists(points_bin):
            raise FileNotFoundError("points3D.bin not found")
        
        points = []
        
        with open(points_bin, "rb") as f:
            num_points = struct.unpack("<Q", f.read(8))[0]
            
            for i in range(min(num_points, limit)):
                # Read point data
                point_id = struct.unpack("<Q", f.read(8))[0]
                x, y, z = struct.unpack("<3d", f.read(24))
                r, g, b = struct.unpack("<3B", f.read(3))
                error = struct.unpack("<d", f.read(8))[0]
                
                # Read track (observations)
                track_length = struct.unpack("<Q", f.read(8))[0]
                # Skip track data (image_id, point2d_idx for each)
                f.read(track_length * 8)  # 4 + 4 bytes per observation
                
                points.append({
                    "id": point_id,
                    "x": x,
                    "y": y,
                    "z": z,
                    "r": r,
                    "g": g,
                    "b": b,
                    "error": error,
                    "num_observations": track_length
                })
        
        return points
    
    @staticmethod
    def get_stats(output_path: str) -> Dict[str, Any]:
        """Get reconstruction statistics.
        
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
        if os.path.exists(images_bin):
            with open(images_bin, "rb") as f:
                stats["num_registered_images"] = struct.unpack("<Q", f.read(8))[0]
        
        # Count 3D points and compute stats
        points_bin = os.path.join(sparse_dir, "points3D.bin")
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
            if os.path.exists(os.path.join(path, "images.bin")):
                return path
        
        return None
