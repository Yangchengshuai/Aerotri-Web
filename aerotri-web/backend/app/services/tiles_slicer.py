"""Spatial slicing and LOD generation for 3D Gaussian Splatting tiles.

This module provides functionality to slice Gaussian splatting data
into spatial tiles and generate multiple LOD levels.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TileInfo:
    """Information about a spatial tile."""
    tile_id: str
    bounding_box: Tuple[float, float, float, float, float, float]  # min_x, min_y, min_z, max_x, max_y, max_z
    indices: np.ndarray  # Indices of splats in this tile
    lod_level: int
    geometric_error: float


class TilesSlicer:
    """Spatial slicer for Gaussian splatting data."""
    
    def __init__(self, max_splats_per_tile: int = 100000):
        """Initialize slicer.
        
        Args:
            max_splats_per_tile: Maximum number of splats per tile
        """
        self.max_splats_per_tile = max_splats_per_tile
    
    def slice_gaussian_data(
        self,
        gaussian_data: Dict,
        output_dir: Path
    ) -> List[TileInfo]:
        """Slice Gaussian data into spatial tiles.
        
        Args:
            gaussian_data: Dictionary containing Gaussian data
            output_dir: Output directory for tiles
            
        Returns:
            List of TileInfo objects
        """
        positions = gaussian_data['positions']
        num_points = positions.shape[0]
        
        # Calculate bounding box
        min_bounds = positions.min(axis=0)
        max_bounds = positions.max(axis=0)
        bbox = (*min_bounds, *max_bounds)
        
        # Simple octree-based slicing
        tiles = []
        
        if num_points <= self.max_splats_per_tile:
            # Single tile
            tile = TileInfo(
                tile_id="0",
                bounding_box=bbox,
                indices=np.arange(num_points),
                lod_level=0,
                geometric_error=1000.0
            )
            tiles.append(tile)
        else:
            # Multiple tiles using octree
            tiles = self._octree_slice(
                positions,
                bbox,
                max_depth=4
            )
        
        return tiles
    
    def _octree_slice(
        self,
        positions: np.ndarray,
        bbox: Tuple[float, ...],
        max_depth: int = 4,
        current_depth: int = 0
    ) -> List[TileInfo]:
        """Recursively slice using octree.
        
        Args:
            positions: Splat positions
            bbox: Bounding box (min_x, min_y, min_z, max_x, max_y, max_z)
            max_depth: Maximum recursion depth
            current_depth: Current depth
            
        Returns:
            List of TileInfo objects
        """
        min_x, min_y, min_z, max_x, max_y, max_z = bbox
        
        # Filter points in this bounding box
        mask = (
            (positions[:, 0] >= min_x) & (positions[:, 0] < max_x) &
            (positions[:, 1] >= min_y) & (positions[:, 1] < max_y) &
            (positions[:, 2] >= min_z) & (positions[:, 2] < max_z)
        )
        indices = np.where(mask)[0]
        
        if len(indices) == 0:
            return []
        
        if len(indices) <= self.max_splats_per_tile or current_depth >= max_depth:
            # Create leaf tile
            tile_bbox = (
                positions[indices, 0].min(),
                positions[indices, 1].min(),
                positions[indices, 2].min(),
                positions[indices, 0].max(),
                positions[indices, 1].max(),
                positions[indices, 2].max()
            )
            geometric_error = self._calculate_geometric_error(tile_bbox, len(indices))
            
            tile = TileInfo(
                tile_id=f"{current_depth}_{hash(tuple(indices[:10])) % 10000}",
                bounding_box=tile_bbox,
                indices=indices,
                lod_level=0,
                geometric_error=geometric_error
            )
            return [tile]
        
        # Split into 8 octants
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2
        mid_z = (min_z + max_z) / 2
        
        tiles = []
        for i in range(8):
            # Calculate octant bounds
            if i & 1:
                oct_min_x, oct_max_x = mid_x, max_x
            else:
                oct_min_x, oct_max_x = min_x, mid_x
            
            if i & 2:
                oct_min_y, oct_max_y = mid_y, max_y
            else:
                oct_min_y, oct_max_y = min_y, mid_y
            
            if i & 4:
                oct_min_z, oct_max_z = mid_z, max_z
            else:
                oct_min_z, oct_max_z = min_z, mid_z
            
            oct_bbox = (oct_min_x, oct_min_y, oct_min_z, oct_max_x, oct_max_y, oct_max_z)
            oct_tiles = self._octree_slice(positions, oct_bbox, max_depth, current_depth + 1)
            tiles.extend(oct_tiles)
        
        return tiles
    
    def _calculate_geometric_error(
        self,
        bbox: Tuple[float, ...],
        num_splats: int
    ) -> float:
        """Calculate geometric error for a tile.
        
        Args:
            bbox: Bounding box
            num_splats: Number of splats in tile
            
        Returns:
            Geometric error value
        """
        min_x, min_y, min_z, max_x, max_y, max_z = bbox
        diagonal = np.sqrt(
            (max_x - min_x) ** 2 +
            (max_y - min_y) ** 2 +
            (max_z - min_z) ** 2
        )
        # Geometric error proportional to tile size and inversely to splat density
        error = diagonal * (1.0 / max(num_splats / 1000, 1.0))
        return float(error)
    
    def generate_lod_levels(
        self,
        gaussian_data: Dict,
        tiles: List[TileInfo],
        lod_levels: List[float] = [1.0, 0.5, 0.25]
    ) -> Dict[int, List[TileInfo]]:
        """Generate multiple LOD levels for tiles.
        
        Args:
            gaussian_data: Original Gaussian data
            tiles: Base level tiles (LOD 0)
            lod_levels: List of LOD ratios (1.0 = full, 0.5 = half, etc.)
            
        Returns:
            Dictionary mapping LOD level to list of TileInfo
        """
        lod_tiles = {0: tiles}
        
        for lod_idx, lod_ratio in enumerate(lod_levels[1:], start=1):
            lod_tiles[lod_idx] = []
            
            for base_tile in tiles:
                # Downsample based on importance (simple random sampling for now)
                num_splats = len(base_tile.indices)
                target_count = int(num_splats * lod_ratio)
                
                if target_count < num_splats:
                    # Random sampling (can be improved with importance-based sampling)
                    sampled_indices = np.random.choice(
                        base_tile.indices,
                        size=target_count,
                        replace=False
                    )
                    sampled_indices = np.sort(sampled_indices)
                else:
                    sampled_indices = base_tile.indices
                
                lod_tile = TileInfo(
                    tile_id=f"{base_tile.tile_id}_L{lod_idx}",
                    bounding_box=base_tile.bounding_box,
                    indices=sampled_indices,
                    lod_level=lod_idx,
                    geometric_error=base_tile.geometric_error * (1.0 / lod_ratio)
                )
                lod_tiles[lod_idx].append(lod_tile)
        
        return lod_tiles


def slice_gaussian_data(
    gaussian_data: Dict,
    output_dir: Path,
    max_splats_per_tile: int = 100000
) -> List[TileInfo]:
    """Convenience function to slice Gaussian data.
    
    Args:
        gaussian_data: Dictionary containing Gaussian data
        output_dir: Output directory
        max_splats_per_tile: Maximum splats per tile
        
    Returns:
        List of TileInfo objects
    """
    slicer = TilesSlicer(max_splats_per_tile=max_splats_per_tile)
    return slicer.slice_gaussian_data(gaussian_data, output_dir)
