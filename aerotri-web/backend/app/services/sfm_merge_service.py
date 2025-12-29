"""SfM merge service for combining partition results."""
import os
import struct
import numpy as np
from typing import List, Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockPartition
from .partition_service import PartitionService


class SFMMergeService:
    """Service for merging partition SfM results."""
    
    @staticmethod
    def read_images_bin(images_bin_path: str, include_points2d: bool = False) -> Dict[str, Dict]:
        """Read COLMAP images.bin file.
        
        Args:
            images_bin_path: Path to images.bin file
            include_points2d: If True, include 2D points data in the result
        
        Returns:
            Dict mapping image_name -> {image_id, qw, qx, qy, qz, tx, ty, tz, camera_id, points2d}
            points2d is a list of (x, y, point3d_id) tuples if include_points2d=True
        """
        images = {}
        with open(images_bin_path, "rb") as f:
            num_images = struct.unpack("<Q", f.read(8))[0]
            # Validate num_images to avoid overflow in range()
            if num_images > 2**31 - 1:  # Python range() limit
                raise RuntimeError(f"Number of images {num_images} exceeds Python range() limit")
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
                
                # Read 2D points
                num_points2d = struct.unpack("<Q", f.read(8))[0]
                if num_points2d > 2**31 - 1:  # Python range() limit
                    raise RuntimeError(f"Number of 2D points {num_points2d} exceeds Python range() limit")
                
                points2d = []
                if include_points2d:
                    for _ in range(int(num_points2d)):
                        x, y = struct.unpack("<2d", f.read(16))
                        point3d_id = struct.unpack("<Q", f.read(8))[0]
                        points2d.append((x, y, point3d_id))
                else:
                    f.read(int(num_points2d) * 24)  # Skip point data
                
                images[image_name] = {
                    "image_id": image_id,
                    "qw": qw, "qx": qx, "qy": qy, "qz": qz,
                    "tx": tx, "ty": ty, "tz": tz,
                    "camera_id": camera_id,
                }
                if include_points2d:
                    images[image_name]["points2d"] = points2d
        return images
    
    @staticmethod
    def read_images_txt(images_txt_path: str) -> Dict[str, Dict]:
        """Read COLMAP/InstantSFM images.txt file.
        
        Returns:
            Dict mapping image_name -> {image_id, qw, qx, qy, qz, tx, ty, tz, camera_id}
        """
        images = {}
        with open(images_txt_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("#"):
                i += 1
                continue
            
            # First line: pose + camera ID + image name
            parts = line.split()
            if len(parts) < 10:
                i += 1
                continue
            
            image_id = int(parts[0])
            qw, qx, qy, qz = map(float, parts[1:5])
            tx, ty, tz = map(float, parts[5:8])
            camera_id = int(parts[8])
            image_name = " ".join(parts[9:])
            
            images[image_name] = {
                "image_id": image_id,
                "qw": qw, "qx": qx, "qy": qy, "qz": qz,
                "tx": tx, "ty": ty, "tz": tz,
                "camera_id": camera_id,
            }
            
            # Skip next line (2D-3D observations)
            if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                i += 2
            else:
                i += 1
        
        return images
    
    @staticmethod
    def read_cameras_bin(cameras_bin_path: str) -> Dict[int, Dict]:
        """Read COLMAP cameras.bin file.
        
        Returns:
            Dict mapping camera_id -> camera parameters
        """
        # COLMAP camera model to parameter count mapping
        # Reference: https://github.com/colmap/colmap/blob/master/src/base/camera_models.h
        MODEL_PARAM_COUNTS = {
            0: 3,   # SIMPLE_PINHOLE
            1: 4,   # PINHOLE
            2: 4,   # SIMPLE_RADIAL
            3: 5,   # RADIAL
            4: 8,   # OPENCV
            5: 8,   # OPENCV_FISHEYE
            6: 12,  # FULL_OPENCV
            7: 4,   # FOV
            8: 4,   # SIMPLE_RADIAL_FISHEYE
            9: 5,   # RADIAL_FISHEYE
            10: 12, # THIN_PRISM_FISHEYE
        }
        
        cameras = {}
        with open(cameras_bin_path, "rb") as f:
            num_cameras = struct.unpack("<Q", f.read(8))[0]
            # Validate num_cameras to avoid overflow in range()
            if num_cameras > 2**31 - 1:  # Python range() limit
                raise RuntimeError(f"Number of cameras {num_cameras} exceeds Python range() limit")
            for _ in range(int(num_cameras)):
                camera_id = struct.unpack("<I", f.read(4))[0]
                model = struct.unpack("<I", f.read(4))[0]
                width = struct.unpack("<Q", f.read(8))[0]
                height = struct.unpack("<Q", f.read(8))[0]
                
                # Get parameter count based on camera model
                num_params = MODEL_PARAM_COUNTS.get(model, 4)  # Default to 4 if unknown model
                # Validate num_params to avoid overflow in struct.unpack
                if num_params > 2**31 - 1:  # Python struct format limit
                    raise RuntimeError(f"Number of camera parameters {num_params} exceeds Python struct format limit")
                if num_params < 0:
                    raise RuntimeError(f"Number of camera parameters {num_params} is negative")
                # Read params as bytes and unpack
                params_bytes = f.read(8 * int(num_params))
                if len(params_bytes) < 8 * num_params:
                    raise RuntimeError(f"Insufficient data for camera {camera_id}: expected {8 * num_params} bytes, got {len(params_bytes)}")
                params = struct.unpack(f"<{int(num_params)}d", params_bytes)
                
                cameras[camera_id] = {
                    "model": model,
                    "width": width,
                    "height": height,
                    "params": params,
                }
        return cameras
    
    @staticmethod
    def read_cameras_txt(cameras_txt_path: str) -> Dict[int, Dict]:
        """Read COLMAP/InstantSFM cameras.txt file.
        
        Returns:
            Dict mapping camera_id -> camera parameters
        """
        cameras = {}
        # Model name to ID mapping (COLMAP standard)
        model_map = {
            "SIMPLE_PINHOLE": 0,
            "PINHOLE": 1,
            "SIMPLE_RADIAL": 2,
            "RADIAL": 3,
            "OPENCV": 4,
            "OPENCV_FISHEYE": 5,
            "FULL_OPENCV": 6,
            "FOV": 7,
            "SIMPLE_RADIAL_FISHEYE": 8,
            "RADIAL_FISHEYE": 9,
            "THIN_PRISM_FISHEYE": 10,
        }
        
        with open(cameras_txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                parts = line.split()
                if len(parts) < 4:
                    continue
                
                camera_id = int(parts[0])
                model_name = parts[1]
                width = int(parts[2])
                height = int(parts[3])
                params = [float(p) for p in parts[4:]]
                
                model_id = model_map.get(model_name, 0)
                
                cameras[camera_id] = {
                    "model": model_id,
                    "width": width,
                    "height": height,
                    "params": tuple(params),
                }
        
        return cameras
    
    @staticmethod
    def read_points3d_bin(points_bin_path: str) -> Dict[int, Dict]:
        """Read COLMAP points3D.bin file.
        
        Returns:
            Dict mapping point3d_id -> {x, y, z, r, g, b, error, track}
        """
        points = {}
        with open(points_bin_path, "rb") as f:
            num_points = struct.unpack("<Q", f.read(8))[0]
            # Validate num_points to avoid overflow in range()
            if num_points > 2**31 - 1:  # Python range() limit
                raise RuntimeError(f"Number of points {num_points} exceeds Python range() limit")
            for _ in range(int(num_points)):
                point_id = struct.unpack("<Q", f.read(8))[0]
                x, y, z = struct.unpack("<3d", f.read(24))
                r, g, b = struct.unpack("<3B", f.read(3))
                error = struct.unpack("<d", f.read(8))[0]
                
                track_length = struct.unpack("<Q", f.read(8))[0]
                # Validate track_length to avoid overflow in range()
                if track_length > 2**31 - 1:  # Python range() limit
                    raise RuntimeError(f"Track length {track_length} exceeds Python range() limit")
                track = []
                for _ in range(int(track_length)):
                    image_id = struct.unpack("<I", f.read(4))[0]
                    point2d_idx = struct.unpack("<I", f.read(4))[0]
                    track.append((int(image_id), int(point2d_idx)))
                
                points[point_id] = {
                    "x": x, "y": y, "z": z,
                    "r": r, "g": g, "b": b,
                    "error": error,
                    "track": track,
                }
        return points
    
    @staticmethod
    def read_points3d_txt(points_txt_path: str) -> Dict[int, Dict]:
        """Read COLMAP/InstantSFM points3D.txt file.
        
        Returns:
            Dict mapping point3d_id -> {x, y, z, r, g, b, error, track}
        """
        points = {}
        with open(points_txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                parts = line.split()
                if len(parts) < 8:
                    continue
                
                point_id = int(parts[0])
                x, y, z = map(float, parts[1:4])
                r, g, b = map(int, parts[4:7])
                error = float(parts[7])
                
                # Track: image_id, point2d_idx pairs
                track_elems = parts[8:]
                track = []
                for j in range(0, len(track_elems), 2):
                    if j + 1 < len(track_elems):
                        image_id = int(track_elems[j])
                        point2d_idx = int(track_elems[j + 1])
                        track.append((image_id, point2d_idx))
                
                points[point_id] = {
                    "x": x, "y": y, "z": z,
                    "r": r, "g": g, "b": b,
                    "error": error,
                    "track": track,
                }
        
        return points
    
    @staticmethod
    def quaternion_to_rotation_matrix(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
        """Convert quaternion to rotation matrix."""
        R = np.array([
            [1 - 2*(qy**2 + qz**2), 2*(qx*qy - qw*qz), 2*(qx*qz + qw*qy)],
            [2*(qx*qy + qw*qz), 1 - 2*(qx**2 + qz**2), 2*(qy*qz - qw*qx)],
            [2*(qx*qz - qw*qy), 2*(qy*qz + qw*qx), 1 - 2*(qx**2 + qy**2)],
        ])
        return R
    
    @staticmethod
    def rotation_matrix_to_quaternion(R: np.ndarray) -> Tuple[float, float, float, float]:
        """Convert rotation matrix to quaternion."""
        trace = np.trace(R)
        if trace > 0:
            s = np.sqrt(trace + 1.0) * 2
            qw = 0.25 * s
            qx = (R[2, 1] - R[1, 2]) / s
            qy = (R[0, 2] - R[2, 0]) / s
            qz = (R[1, 0] - R[0, 1]) / s
        else:
            if R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
                s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
                qw = (R[2, 1] - R[1, 2]) / s
                qx = 0.25 * s
                qy = (R[0, 1] + R[1, 0]) / s
                qz = (R[0, 2] + R[2, 0]) / s
            elif R[1, 1] > R[2, 2]:
                s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
                qw = (R[0, 2] - R[2, 0]) / s
                qx = (R[0, 1] + R[1, 0]) / s
                qy = 0.25 * s
                qz = (R[1, 2] + R[2, 1]) / s
            else:
                s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
                qw = (R[1, 0] - R[0, 1]) / s
                qx = (R[0, 2] + R[2, 0]) / s
                qy = (R[1, 2] + R[2, 1]) / s
                qz = 0.25 * s
        return (qw, qx, qy, qz)
    
    @staticmethod
    def estimate_rigid_transform(
        source_poses: List[Tuple[np.ndarray, np.ndarray]],
        target_poses: List[Tuple[np.ndarray, np.ndarray]],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Estimate rigid transformation (R, t) from source to target using SVD.
        
        Args:
            source_poses: List of (R, t) tuples in source coordinate system
            target_poses: List of (R, t) tuples in target coordinate system
            
        Returns:
            (R_transform, t_transform) such that target = R_transform @ source + t_transform
        """
        if len(source_poses) < 3:
            # Fallback to identity if not enough points
            return np.eye(3), np.zeros(3)
        
        # Extract camera centers
        source_centers = np.array([-R.T @ t for R, t in source_poses])
        target_centers = np.array([-R.T @ t for R, t in target_poses])
        
        # Center the points
        source_mean = source_centers.mean(axis=0)
        target_mean = target_centers.mean(axis=0)
        source_centered = source_centers - source_mean
        target_centered = target_centers - target_mean
        
        # Compute covariance matrix
        H = source_centered.T @ target_centered
        
        # SVD
        U, S, Vt = np.linalg.svd(H)
        R_transform = Vt.T @ U.T
        
        # Ensure proper rotation (det(R) = 1)
        if np.linalg.det(R_transform) < 0:
            Vt[-1, :] *= -1
            R_transform = Vt.T @ U.T
        
        # Compute translation
        t_transform = target_mean - R_transform @ source_mean
        
        return R_transform, t_transform
    
    @staticmethod
    def estimate_sim3_transform(
        source_poses: List[Tuple[np.ndarray, np.ndarray]],
        target_poses: List[Tuple[np.ndarray, np.ndarray]],
    ) -> Tuple[float, np.ndarray, np.ndarray]:
        """Estimate Sim3 transformation (s, R, t) from source to target.
        
        Sim3 is a similarity transformation: target = s * R * source + t
        
        Args:
            source_poses: List of (R, t) tuples in source coordinate system
            target_poses: List of (R, t) tuples in target coordinate system
            
        Returns:
            (s, R_transform, t_transform) such that target = s * R_transform @ source + t_transform
        """
        if len(source_poses) < 3:
            # Fallback to identity if not enough points
            return 1.0, np.eye(3), np.zeros(3)
        
        # Extract camera centers
        source_centers = np.array([-R.T @ t for R, t in source_poses])
        target_centers = np.array([-R.T @ t for R, t in target_poses])
        
        # Center the points
        source_mean = source_centers.mean(axis=0)
        target_mean = target_centers.mean(axis=0)
        source_centered = source_centers - source_mean
        target_centered = target_centers - target_mean
        
        # Compute covariance matrix
        H = source_centered.T @ target_centered
        
        # SVD for rotation
        U, S, Vt = np.linalg.svd(H)
        R_transform = Vt.T @ U.T
        
        # Ensure proper rotation (det(R) = 1)
        if np.linalg.det(R_transform) < 0:
            Vt[-1, :] *= -1
            R_transform = Vt.T @ U.T
        
        # Estimate scale
        source_rotated = source_centered @ R_transform.T
        scale_nom = np.sum(target_centered * source_rotated)
        scale_denom = np.sum(source_rotated**2)
        s = scale_nom / scale_denom if scale_denom > 1e-10 else 1.0
        
        # Ensure scale is positive and reasonable
        if s <= 0 or np.isnan(s) or s > 10.0 or s < 0.1:
            s = 1.0
        
        # Compute translation
        t_transform = target_mean - s * (source_mean @ R_transform.T)
        
        return s, R_transform, t_transform
    
    @staticmethod
    async def merge_partitions(
        block: Block,
        partitions: List[BlockPartition],
        output_sparse_dir: str,
        merge_strategy: str,
        ctx,
        db: AsyncSession,
    ):
        """Merge partition SfM results into a single sparse reconstruction.
        
        Args:
            block: Block instance
            partitions: List of BlockPartition instances (sorted by index)
            output_sparse_dir: Output directory for merged sparse/0
            merge_strategy: Merge strategy ("rigid_keep_one" or future strategies)
            ctx: Task context for logging
            db: Database session
        """
        from ..models import BlockPartition
        
        os.makedirs(output_sparse_dir, exist_ok=True)
        merge_log_path = os.path.join(os.path.dirname(output_sparse_dir), "run_merge.log")
        
        ctx.write_log_line(f"[Merge] Starting merge of {len(partitions)} partitions")
        
        # Read all partition results
        partition_data = []
        for partition in sorted(partitions, key=lambda p: p.index):
            partition_sparse = os.path.join(
                block.output_path or "",
                "partitions",
                f"partition_{partition.index}",
                "sparse",
                "0",
            )
            
            images_bin = os.path.join(partition_sparse, "images.bin")
            images_txt = os.path.join(partition_sparse, "images.txt")
            cameras_bin = os.path.join(partition_sparse, "cameras.bin")
            cameras_txt = os.path.join(partition_sparse, "cameras.txt")
            points_bin = os.path.join(partition_sparse, "points3D.bin")
            points_txt = os.path.join(partition_sparse, "points3D.txt")
            
            # Read images (support both binary and text formats)
            # Include 2D points data for proper merging
            if os.path.exists(images_bin):
                images = SFMMergeService.read_images_bin(images_bin, include_points2d=True)
            elif os.path.exists(images_txt):
                images = SFMMergeService.read_images_txt(images_txt)
                # For text format, we don't have 2D points easily, so set empty
                for img_name in images:
                    images[img_name]["points2d"] = []
            else:
                raise RuntimeError(f"Partition {partition.index} missing images.bin or images.txt")
            
            # Read cameras (support both binary and text formats)
            if os.path.exists(cameras_bin):
                cameras = SFMMergeService.read_cameras_bin(cameras_bin)
            elif os.path.exists(cameras_txt):
                cameras = SFMMergeService.read_cameras_txt(cameras_txt)
            else:
                cameras = {}
            
            # Read points (support both binary and text formats)
            if os.path.exists(points_bin):
                points = SFMMergeService.read_points3d_bin(points_bin)
            elif os.path.exists(points_txt):
                points = SFMMergeService.read_points3d_txt(points_txt)
            else:
                points = {}
            
            partition_data.append({
                "partition": partition,
                "images": images,
                "cameras": cameras,
                "points": points,
            })
            
            ctx.write_log_line(f"[Merge] Partition {partition.index}: {len(images)} images, {len(points)} points")
        
        if not partition_data:
            raise RuntimeError("No partition data to merge")
        
        # Use first partition as reference
        ref_data = partition_data[0]
        merged_images = {}
        merged_cameras = {}
        merged_points = {}
        
        # Add reference partition images and cameras
        # Reassign IDs starting from 1 to avoid overflow issues
        image_id_map = {}  # old_id -> new_id
        camera_id_map = {}  # old_id -> new_id
        point_id_map = {}  # old_id -> new_id
        
        next_image_id = 1
        next_camera_id = 1
        next_point_id = 1
        
        # Remap reference partition IDs
        for img_name, img_data in ref_data["images"].items():
            old_img_id = img_data["image_id"]
            old_cam_id = img_data["camera_id"]
            
            # Map camera ID
            if old_cam_id not in camera_id_map:
                camera_id_map[old_cam_id] = next_camera_id
                next_camera_id += 1
            
            # Map image ID
            image_id_map[old_img_id] = next_image_id
            new_img_data = img_data.copy()
            new_img_data["image_id"] = next_image_id
            new_img_data["camera_id"] = camera_id_map[old_cam_id]
            
            # Remap 2D points: update point3d_id references
            if "points2d" in new_img_data:
                remapped_points2d = []
                for x, y, old_point3d_id in new_img_data["points2d"]:
                    # point3d_id will be remapped when we process points
                    # For now, keep the old ID (we'll update it later)
                    remapped_points2d.append((x, y, old_point3d_id))
                new_img_data["points2d"] = remapped_points2d
            else:
                new_img_data["points2d"] = []
            
            merged_images[img_name] = new_img_data
            next_image_id += 1
        
        # Add cameras
        for old_cam_id, cam_data in ref_data["cameras"].items():
            if old_cam_id in camera_id_map:
                merged_cameras[camera_id_map[old_cam_id]] = cam_data.copy()
        
        # Add points with remapped IDs
        for old_pt_id, pt_data in ref_data["points"].items():
            point_id_map[old_pt_id] = next_point_id
            new_pt_data = pt_data.copy()
            # Remap track image_ids
            new_track = []
            for old_img_id, point2d_idx in pt_data["track"]:
                if old_img_id in image_id_map:
                    new_track.append((image_id_map[old_img_id], point2d_idx))
            new_pt_data["track"] = new_track
            merged_points[next_point_id] = new_pt_data
            next_point_id += 1
        
        # Update 2D points in merged_images: remap point3d_id references
        # Build a mapping from (image_id, point2d_idx) to new point3d_id for reference partition
        # This helps us update 2D points correctly
        point2d_to_point3d = {}  # (image_id, point2d_idx) -> new_point3d_id
        for new_pt_id, pt_data in merged_points.items():
            for new_img_id, point2d_idx in pt_data["track"]:
                point2d_to_point3d[(new_img_id, point2d_idx)] = new_pt_id
        
        # Update 2D points in merged_images with remapped point3d_id
        # IMPORTANT: Keep ALL 2D points to maintain point2d_idx correspondence with tracks
        # Only update point3d_id references, don't remove points
        for img_name, img_data in merged_images.items():
            if "points2d" in img_data and img_data["points2d"]:
                updated_points2d = []
                img_id = img_data["image_id"]
                for idx, (x, y, old_point3d_id) in enumerate(img_data["points2d"]):
                    # Try to find the new point3d_id using point2d_idx
                    point2d_idx = idx  # point2d_idx is the index in the points2d list
                    key = (img_id, point2d_idx)
                    if key in point2d_to_point3d:
                        new_point3d_id = point2d_to_point3d[key]
                        updated_points2d.append((x, y, new_point3d_id))
                    elif old_point3d_id in point_id_map:
                        # Fallback: use point_id_map if available
                        new_point3d_id = point_id_map[old_point3d_id]
                        updated_points2d.append((x, y, new_point3d_id))
                    else:
                        # Keep the point but mark as invalid (UINT64_MAX)
                        # This ensures point2d_idx correspondence is maintained
                        updated_points2d.append((x, y, 18446744073709551615))  # UINT64_MAX
                img_data["points2d"] = updated_points2d
        
        ctx.write_log_line(f"[Merge] Reference partition (0): {len(merged_images)} images, {len(merged_points)} points")
        
        # Merge subsequent partitions with rigid alignment
        
        for i in range(1, len(partition_data)):
            part_data = partition_data[i]
            partition = part_data["partition"]
            
            ctx.write_log_line(f"[Merge] Aligning partition {partition.index} to reference")
            
            # Find overlap images (images that appear in both merged result and current partition)
            # Use merged_images as reference (contains all previously merged images)
            curr_images = part_data["images"]
            
            overlap_images = set(merged_images.keys()) & set(curr_images.keys())
            if len(overlap_images) < 3:
                ctx.write_log_line(f"[Merge] Warning: Only {len(overlap_images)} overlap images, alignment may be poor")
            
            if len(overlap_images) >= 3:
                # Extract poses for overlap images
                source_poses = []
                target_poses = []
                
                for img_name in overlap_images:
                    # Source: current partition
                    src_img = curr_images[img_name]
                    src_R = SFMMergeService.quaternion_to_rotation_matrix(
                        src_img["qw"], src_img["qx"], src_img["qy"], src_img["qz"]
                    )
                    src_t = np.array([src_img["tx"], src_img["ty"], src_img["tz"]])
                    source_poses.append((src_R, src_t))
                    
                    # Target: merged result (reference)
                    tgt_img = merged_images[img_name]
                    tgt_R = SFMMergeService.quaternion_to_rotation_matrix(
                        tgt_img["qw"], tgt_img["qx"], tgt_img["qy"], tgt_img["qz"]
                    )
                    tgt_t = np.array([tgt_img["tx"], tgt_img["ty"], tgt_img["tz"]])
                    target_poses.append((tgt_R, tgt_t))
                
                # Estimate transform based on merge strategy
                if merge_strategy == "sim3_keep_one":
                    s_transform, R_transform, t_transform = SFMMergeService.estimate_sim3_transform(
                        source_poses, target_poses
                    )
                    ctx.write_log_line(f"[Merge] Estimated Sim3 transform for partition {partition.index}: scale={s_transform:.6f}")
                else:
                    # Default: rigid transform
                    R_transform, t_transform = SFMMergeService.estimate_rigid_transform(
                        source_poses, target_poses
                    )
                    s_transform = 1.0
                    ctx.write_log_line(f"[Merge] Estimated rigid transform for partition {partition.index}")
            else:
                # Fallback: identity transform
                R_transform = np.eye(3)
                t_transform = np.zeros(3)
                s_transform = 1.0
                ctx.write_log_line(f"[Merge] Using identity transform for partition {partition.index} (insufficient overlap)")
            
            # Initialize ID mappings for current partition BEFORE processing images
            # Build camera_id mapping for current partition first
            partition_camera_id_to_global = {}
            for old_cam_id in part_data["cameras"].keys():
                if old_cam_id not in partition_camera_id_to_global:
                    # Check if camera already exists in merged cameras by comparing params
                    # Use tolerance-based comparison for camera parameters to handle slight differences
                    # from independent estimation in different partitions
                    cam_data = part_data["cameras"][old_cam_id]
                    found_existing = False
                    
                    def camera_params_equal(cam1, cam2, tolerance=1e-2):
                        """Compare camera parameters with tolerance for numerical differences."""
                        if (cam1["model"] != cam2["model"] or
                            cam1["width"] != cam2["width"] or
                            cam1["height"] != cam2["height"]):
                            return False
                        params1 = cam1["params"]
                        params2 = cam2["params"]
                        if len(params1) != len(params2):
                            return False
                        # Use relative tolerance for focal length, absolute for distortion
                        for i, (p1, p2) in enumerate(zip(params1, params2)):
                            if i < 2:  # fx, fy: use relative tolerance (1%)
                                if abs(p1 - p2) / max(abs(p1), abs(p2), 1.0) > tolerance:
                                    return False
                            else:  # cx, cy, distortion: use absolute tolerance
                                if abs(p1 - p2) > tolerance:
                                    return False
                        return True
                    
                    for merged_cam_id, merged_cam_data in merged_cameras.items():
                        if camera_params_equal(merged_cam_data, cam_data, tolerance=1e-2):
                            partition_camera_id_to_global[old_cam_id] = merged_cam_id
                            found_existing = True
                            # Optionally: average the parameters for better accuracy
                            # For now, keep the reference partition's parameters
                            break
                    if not found_existing:
                        # Add new camera (truly different camera)
                        partition_camera_id_to_global[old_cam_id] = next_camera_id
                        merged_cameras[next_camera_id] = cam_data.copy()
                        next_camera_id += 1
            
            # Initialize image_id mapping (will be built during image processing)
            partition_image_id_to_global = {}
            
            # Transform and add images from current partition
            for img_name, img_data in curr_images.items():
                if img_name in merged_images:
                    # Overlap image: keep the one from later partition (as per user requirement)
                    # Update the existing entry with transformed pose
                    qw, qx, qy, qz = img_data["qw"], img_data["qx"], img_data["qy"], img_data["qz"]
                    tx, ty, tz = img_data["tx"], img_data["ty"], img_data["tz"]
                    
                    # Transform pose
                    # COLMAP stores world2cam: (R_w2c, t_w2c)
                    # Camera center: C = -R_w2c^T * t_w2c
                    R_w2c = SFMMergeService.quaternion_to_rotation_matrix(qw, qx, qy, qz)
                    t_w2c = np.array([tx, ty, tz])
                    
                    # Extract camera center
                    C_old = -R_w2c.T @ t_w2c
                    
                    # Apply Sim3 or Rigid transform to camera center
                    if merge_strategy == "sim3_keep_one":
                        C_new = s_transform * (R_transform @ C_old) + t_transform
                    else:
                        C_new = R_transform @ C_old + t_transform
                    
                    # Update world2cam
                    R_w2c_new = R_w2c @ R_transform.T
                    t_w2c_new = -R_w2c_new @ C_new
                    
                    qw_new, qx_new, qy_new, qz_new = SFMMergeService.rotation_matrix_to_quaternion(R_w2c_new)
                    
                    # Update merged image (keep later partition's pose as per requirement)
                    merged_images[img_name].update({
                        "qw": qw_new, "qx": qx_new, "qy": qy_new, "qz": qz_new,
                        "tx": float(t_w2c_new[0]), "ty": float(t_w2c_new[1]), "tz": float(t_w2c_new[2]),
                    })
                    # Add to image_id mapping for overlap images
                    partition_image_id_to_global[img_data["image_id"]] = merged_images[img_name]["image_id"]
                    
                    # Update 2D points for overlap images: merge 2D points from current partition
                    # Keep existing 2D points but add new ones from current partition
                    if "points2d" in img_data and img_data["points2d"]:
                        existing_points2d = merged_images[img_name].get("points2d", [])
                        # For overlap images, we should merge 2D points
                        # But to avoid duplicates, we'll keep the existing ones and update point3d_id references later
                        # For now, just ensure points2d exists
                        if "points2d" not in merged_images[img_name]:
                            merged_images[img_name]["points2d"] = []
                else:
                    # New image: transform and add
                    qw, qx, qy, qz = img_data["qw"], img_data["qx"], img_data["qy"], img_data["qz"]
                    tx, ty, tz = img_data["tx"], img_data["ty"], img_data["tz"]
                    
                    # Transform pose
                    # COLMAP stores world2cam: (R_w2c, t_w2c)
                    # Camera center: C = -R_w2c^T * t_w2c
                    R_w2c = SFMMergeService.quaternion_to_rotation_matrix(qw, qx, qy, qz)
                    t_w2c = np.array([tx, ty, tz])
                    
                    # Extract camera center
                    C_old = -R_w2c.T @ t_w2c
                    
                    # Apply Sim3 or Rigid transform to camera center
                    if merge_strategy == "sim3_keep_one":
                        C_new = s_transform * (R_transform @ C_old) + t_transform
                    else:
                        C_new = R_transform @ C_old + t_transform
                    
                    # Update world2cam
                    R_w2c_new = R_w2c @ R_transform.T
                    t_w2c_new = -R_w2c_new @ C_new
                    
                    qw_new, qx_new, qy_new, qz_new = SFMMergeService.rotation_matrix_to_quaternion(R_w2c_new)
                    
                    # Assign new IDs
                    old_cam_id = img_data["camera_id"]
                    new_cam_id = partition_camera_id_to_global.get(old_cam_id, next_camera_id)
                    if old_cam_id not in partition_camera_id_to_global:
                        # Add camera if not exists
                        if old_cam_id in part_data["cameras"]:
                            merged_cameras[next_camera_id] = part_data["cameras"][old_cam_id].copy()
                            partition_camera_id_to_global[old_cam_id] = next_camera_id
                            new_cam_id = next_camera_id
                            next_camera_id += 1
                    
                    # Check for ID overflow (32-bit unsigned int max: 4294967295)
                    MAX_UINT32 = 4294967295
                    if next_image_id > MAX_UINT32:
                        raise RuntimeError(f"Image ID overflow: {next_image_id} exceeds 32-bit unsigned integer limit ({MAX_UINT32})")
                    if new_cam_id > MAX_UINT32:
                        raise RuntimeError(f"Camera ID overflow: {new_cam_id} exceeds 32-bit unsigned integer limit ({MAX_UINT32})")
                    
                    # Add 2D points from current partition for new images
                    points2d = img_data.get("points2d", [])
                    merged_images[img_name] = {
                        "image_id": next_image_id,
                        "qw": qw_new, "qx": qx_new, "qy": qy_new, "qz": qz_new,
                        "tx": float(t_w2c_new[0]), "ty": float(t_w2c_new[1]), "tz": float(t_w2c_new[2]),
                        "camera_id": new_cam_id,
                        "points2d": points2d,  # Will be remapped later
                    }
                    partition_image_id_to_global[img_data["image_id"]] = next_image_id
                    next_image_id += 1
            
            # Build partition point_id mapping for current partition
            partition_point_id_map = {}  # old_pt_id -> new_point_id
            
            # Transform and add points
            for pt_id, pt_data in part_data["points"].items():
                x, y, z = pt_data["x"], pt_data["y"], pt_data["z"]
                pt_3d = np.array([x, y, z])
                # Apply Sim3 or Rigid transform
                pt_3d_transformed = s_transform * (R_transform @ pt_3d) + t_transform
                
                # Remap track image_ids from partition IDs to global IDs
                new_track = []
                MAX_UINT32 = 4294967295
                for old_image_id, point2d_idx in pt_data["track"]:
                    if old_image_id in partition_image_id_to_global:
                        new_image_id = partition_image_id_to_global[old_image_id]
                        # Check for overflow and ensure values are within valid range
                        if new_image_id > MAX_UINT32:
                            raise RuntimeError(f"Track image_id overflow: {new_image_id} exceeds 32-bit unsigned integer limit")
                        # Ensure point2d_idx is a valid integer within range
                        point2d_idx_int = int(point2d_idx)
                        if point2d_idx_int < 0:
                            raise RuntimeError(f"Track point2d_idx is negative: {point2d_idx_int}")
                        if point2d_idx_int > MAX_UINT32:
                            raise RuntimeError(f"Track point2d_idx overflow: {point2d_idx_int} exceeds 32-bit unsigned integer limit")
                        new_track.append((int(new_image_id), point2d_idx_int))
                    # If image_id not in mapping, skip this observation (invalid reference)
                
                # Check point ID overflow
                MAX_UINT64 = 18446744073709551615  # 64-bit unsigned int for points3D
                if next_point_id > MAX_UINT64:
                    raise RuntimeError(f"Point ID overflow: {next_point_id} exceeds 64-bit unsigned integer limit")
                
                # Map old point ID to new point ID
                partition_point_id_map[pt_id] = next_point_id
                
                # Use new point ID
                merged_points[next_point_id] = {
                    "x": float(pt_3d_transformed[0]),
                    "y": float(pt_3d_transformed[1]),
                    "z": float(pt_3d_transformed[2]),
                    "r": pt_data["r"],
                    "g": pt_data["g"],
                    "b": pt_data["b"],
                    "error": pt_data["error"],
                    "track": new_track,  # Use remapped track
                }
                next_point_id += 1
            
            # Update 2D points for images from current partition: remap point3d_id references
            # Build mapping from (image_id, point2d_idx) to new point3d_id
            partition_point2d_to_point3d = {}
            for new_pt_id, pt_data in merged_points.items():
                # Only include points that were just added (in partition_point_id_map values)
                if new_pt_id in partition_point_id_map.values():
                    for new_img_id, point2d_idx in pt_data["track"]:
                        if new_img_id in partition_image_id_to_global.values():
                            partition_point2d_to_point3d[(new_img_id, point2d_idx)] = new_pt_id
            
            # Update 2D points for images from current partition
            for img_name, img_data in curr_images.items():
                if img_name in merged_images and "points2d" in img_data:
                    merged_img_data = merged_images[img_name]
                    img_id = merged_img_data["image_id"]
                    old_points2d = img_data["points2d"]
                    updated_points2d = []
                    
                    for idx, (x, y, old_point3d_id) in enumerate(old_points2d):
                        # Try to find new point3d_id using point2d_idx
                        point2d_idx = idx
                        key = (img_id, point2d_idx)
                        if key in partition_point2d_to_point3d:
                            new_point3d_id = partition_point2d_to_point3d[key]
                            updated_points2d.append((x, y, new_point3d_id))
                        elif old_point3d_id in partition_point_id_map:
                            # Fallback: use partition_point_id_map
                            new_point3d_id = partition_point_id_map[old_point3d_id]
                            updated_points2d.append((x, y, new_point3d_id))
                        # If neither works, skip this point (invalid reference)
                    
                    # For overlap images, merge with existing points2d
                    if "points2d" in merged_img_data and merged_img_data["points2d"]:
                        # Keep existing valid points and add new valid ones
                        existing_points2d = merged_img_data["points2d"]
                        # Simple merge: append new points (could be optimized to avoid duplicates)
                        merged_img_data["points2d"] = existing_points2d + updated_points2d
                    else:
                        merged_img_data["points2d"] = updated_points2d
            
            ctx.write_log_line(f"[Merge] Partition {partition.index} merged: {len(merged_images)} total images, {len(merged_points)} total points")
        
        # Write merged results
        ctx.write_log_line(f"[Merge] Writing merged results to {output_sparse_dir}")
        
        # Model ID to name mapping for text output
        model_id_to_name = {
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
        
        # Write cameras.bin
        # COLMAP cameras.bin format does NOT include num_params field
        # Format: num_cameras (Q), then for each camera:
        #   camera_id (I), model (I), width (Q), height (Q), params[] (d array, no count)
        cameras_bin_path = os.path.join(output_sparse_dir, "cameras.bin")
        MAX_UINT32 = 4294967295
        with open(cameras_bin_path, "wb") as f:
            f.write(struct.pack("<Q", len(merged_cameras)))
            for cam_id, cam_data in sorted(merged_cameras.items()):
                if cam_id > MAX_UINT32:
                    raise RuntimeError(f"Cannot write camera_id {cam_id}: exceeds 32-bit unsigned integer limit ({MAX_UINT32})")
                if cam_data["model"] > MAX_UINT32:
                    raise RuntimeError(f"Cannot write camera model {cam_data['model']}: exceeds 32-bit unsigned integer limit")
                f.write(struct.pack("<I", cam_id))
                f.write(struct.pack("<I", cam_data["model"]))
                f.write(struct.pack("<Q", cam_data["width"]))
                f.write(struct.pack("<Q", cam_data["height"]))
                # Write params directly without num_params field (COLMAP format)
                params = cam_data["params"]
                f.write(struct.pack(f"<{len(params)}d", *params))
        
        # Also write cameras.txt for compatibility (COLMAP sometimes has issues with binary format)
        cameras_txt_path = os.path.join(output_sparse_dir, "cameras.txt")
        with open(cameras_txt_path, "w", encoding="utf-8") as f:
            f.write("# Camera list with one line of data per camera:\n")
            f.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
            f.write(f"# Number of cameras: {len(merged_cameras)}\n")
            for cam_id, cam_data in sorted(merged_cameras.items()):
                model_name = model_id_to_name.get(cam_data["model"], f"UNKNOWN_{cam_data['model']}")
                params_str = " ".join(str(p) for p in cam_data["params"])
                f.write(f"{cam_id} {model_name} {cam_data['width']} {cam_data['height']} {params_str}\n")
        
        # Write images.bin
        images_bin_path = os.path.join(output_sparse_dir, "images.bin")
        MAX_UINT32 = 4294967295
        with open(images_bin_path, "wb") as f:
            f.write(struct.pack("<Q", len(merged_images)))
            for img_name, img_data in sorted(merged_images.items(), key=lambda x: x[1]["image_id"]):
                img_id = img_data["image_id"]
                cam_id = img_data["camera_id"]
                if img_id > MAX_UINT32:
                    raise RuntimeError(f"Cannot write image_id {img_id}: exceeds 32-bit unsigned integer limit ({MAX_UINT32})")
                if cam_id > MAX_UINT32:
                    raise RuntimeError(f"Cannot write camera_id {cam_id}: exceeds 32-bit unsigned integer limit ({MAX_UINT32})")
                f.write(struct.pack("<I", img_id))
                f.write(struct.pack("<4d", img_data["qw"], img_data["qx"], img_data["qy"], img_data["qz"]))
                f.write(struct.pack("<3d", img_data["tx"], img_data["ty"], img_data["tz"]))
                f.write(struct.pack("<I", cam_id))
                f.write(img_name.encode("utf-8") + b"\x00")
                
                # Write 2D points if available
                points2d = img_data.get("points2d", [])
                f.write(struct.pack("<Q", len(points2d)))
                for x, y, point3d_id in points2d:
                    f.write(struct.pack("<2d", x, y))
                    f.write(struct.pack("<Q", point3d_id))
        
        # Also write images.txt for compatibility
        images_txt_path = os.path.join(output_sparse_dir, "images.txt")
        with open(images_txt_path, "w", encoding="utf-8") as f:
            f.write("# Image list with two lines of data per image:\n")
            f.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
            f.write("#   POINTS2D[] as (X, Y, IMAGE_ID, POINT2D_IDX)\n")
            f.write(f"# Number of images: {len(merged_images)}, mean observations per image: 0\n")
            for img_name, img_data in sorted(merged_images.items(), key=lambda x: x[1]["image_id"]):
                f.write(f"{img_data['image_id']} {img_data['qw']} {img_data['qx']} {img_data['qy']} {img_data['qz']} "
                       f"{img_data['tx']} {img_data['ty']} {img_data['tz']} {img_data['camera_id']} {img_name}\n")
                # Empty 2D points line
                f.write("\n")
        
        # Write points3D.bin
        points_bin_path = os.path.join(output_sparse_dir, "points3D.bin")
        with open(points_bin_path, "wb") as f:
            f.write(struct.pack("<Q", len(merged_points)))
            for pt_id, pt_data in sorted(merged_points.items()):
                f.write(struct.pack("<Q", pt_id))
                f.write(struct.pack("<3d", pt_data["x"], pt_data["y"], pt_data["z"]))
                f.write(struct.pack("<3B", pt_data["r"], pt_data["g"], pt_data["b"]))
                f.write(struct.pack("<d", pt_data["error"]))
                track = pt_data["track"]
                f.write(struct.pack("<Q", len(track)))
                MAX_UINT32 = 4294967295
                for image_id, point2d_idx in track:
                    # Ensure values are integers and within valid range
                    image_id_int = int(image_id)
                    point2d_idx_int = int(point2d_idx)
                    if image_id_int < 0 or image_id_int > MAX_UINT32:
                        raise RuntimeError(f"Cannot write track image_id {image_id_int}: exceeds 32-bit unsigned integer limit ({MAX_UINT32})")
                    if point2d_idx_int < 0 or point2d_idx_int > MAX_UINT32:
                        raise RuntimeError(f"Cannot write track point2d_idx {point2d_idx_int}: exceeds 32-bit unsigned integer limit ({MAX_UINT32})")
                    f.write(struct.pack("<I", image_id_int))
                    f.write(struct.pack("<I", point2d_idx_int))
        
        # Also write points3D.txt for compatibility
        points_txt_path = os.path.join(output_sparse_dir, "points3D.txt")
        with open(points_txt_path, "w", encoding="utf-8") as f:
            f.write("# 3D point list with one line of data per point:\n")
            f.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
            total_obs = sum(len(pt.get("track", [])) for pt in merged_points.values())
            mean_track = (total_obs / len(merged_points)) if merged_points else 0.0
            f.write(f"# Number of points: {len(merged_points)}, mean track length: {mean_track:.1f}\n")
            for pt_id, pt_data in sorted(merged_points.items()):
                track = pt_data.get("track", [])
                track_str = " ".join(f"{img_id} {pt2d_idx}" for img_id, pt2d_idx in track)
                f.write(f"{pt_id} {pt_data['x']} {pt_data['y']} {pt_data['z']} "
                       f"{pt_data['r']} {pt_data['g']} {pt_data['b']} {pt_data['error']} {track_str}\n")

        # Write merged stats sidecar for reprojection error (InstantSfM ERROR often 0 in merged bin-only output)
        try:
            from .result_reader import ResultReader

            total_points = len(merged_points)
            total_obs = 0
            for _, pt in merged_points.items():
                total_obs += len(pt.get("track", []) or [])

            # Weighted reprojection error from per-partition stats (best-effort)
            w_err_sum = 0.0
            w_obs_sum = 0
            if block.output_path:
                for part in sorted(partitions, key=lambda p: p.index):
                    ps = ResultReader.read_partition_stats(block.output_path, part.index) or {}
                    p_obs = int(ps.get("num_observations", 0) or 0)
                    p_err = float(ps.get("mean_reprojection_error", 0.0) or 0.0)
                    if p_obs > 0 and p_err > 0.0:
                        w_obs_sum += p_obs
                        w_err_sum += p_err * p_obs

            merged_stats = {
                "version": 1,
                "merge_strategy": merge_strategy,
                "num_registered_images": len(merged_images),
                "num_points3d": total_points,
                "num_observations": total_obs,
                "mean_track_length": (total_obs / total_points) if total_points > 0 else 0.0,
                "mean_reprojection_error": (w_err_sum / w_obs_sum) if w_obs_sum > 0 else 0.0,
                "source_partition_observations": w_obs_sum,
            }

            merged_stats_path = os.path.join(output_sparse_dir, "merged_stats.json")
            with open(merged_stats_path, "w", encoding="utf-8") as f:
                import json
                json.dump(merged_stats, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        
        ctx.write_log_line(f"[Merge] Merge completed: {len(merged_images)} images, {len(merged_cameras)} cameras, {len(merged_points)} points")

