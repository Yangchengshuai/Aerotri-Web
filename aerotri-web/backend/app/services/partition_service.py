"""Partition service for large-scale SfM blocks."""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockPartition, AsyncSessionLocal
from .workspace_service import WorkspaceService


class PartitionDefinition:
    """In-memory partition definition (before saving to DB)."""
    
    def __init__(
        self,
        index: int,
        image_names: List[str],
        overlap_with_prev: int = 0,
        overlap_with_next: int = 0,
    ):
        self.index = index
        self.image_names = image_names
        self.image_start_name = image_names[0] if image_names else None
        self.image_end_name = image_names[-1] if image_names else None
        self.image_count = len(image_names)
        self.overlap_with_prev = overlap_with_prev
        self.overlap_with_next = overlap_with_next
        self.name = f"P{index + 1}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "image_start_name": self.image_start_name,
            "image_end_name": self.image_end_name,
            "image_count": self.image_count,
            "overlap_with_prev": self.overlap_with_prev,
            "overlap_with_next": self.overlap_with_next,
            "image_names": self.image_names,  # For preview only
        }


class PartitionService:
    """Service for building and managing partitions."""
    
    @staticmethod
    def get_image_list(block: Block) -> List[str]:
        """Get sorted list of image filenames for a block.
        
        Args:
            block: Block instance
            
        Returns:
            Sorted list of image filenames
        """
        image_dir = block.working_image_path or block.image_path
        if not image_dir or not os.path.isdir(image_dir):
            return []
        
        image_files = WorkspaceService.list_source_images(image_dir)
        return sorted([f.name for f in image_files])
    
    @staticmethod
    def build_partitions_by_name_with_overlap(
        image_names: List[str],
        partition_size: int = 1000,
        overlap: int = 150,
    ) -> List[PartitionDefinition]:
        """Build partitions by sorting images by name with overlap.
        
        Args:
            image_names: Sorted list of image filenames
            partition_size: Number of images per partition
            overlap: Number of overlapping images between adjacent partitions
            
        Returns:
            List of PartitionDefinition objects
        """
        if not image_names:
            return []
        
        if partition_size <= 0:
            raise ValueError("partition_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= partition_size:
            raise ValueError("overlap must be less than partition_size")
        
        partitions = []
        total_images = len(image_names)
        
        # First partition: [0, partition_size)
        start_idx = 0
        partition_index = 0
        
        while start_idx < total_images:
            # Calculate end index for this partition
            end_idx = min(start_idx + partition_size, total_images)
            
            # Get image names for this partition
            partition_images = image_names[start_idx:end_idx]
            
            # Calculate overlaps
            overlap_with_prev = 0
            if partition_index > 0:
                # Previous partition's last 'overlap' images
                prev_start = max(0, start_idx - partition_size)
                prev_end = start_idx
                overlap_with_prev = len(set(image_names[prev_start:prev_end]) & set(partition_images))
            
            overlap_with_next = 0
            if end_idx < total_images:
                # Next partition's first 'overlap' images (if any)
                next_start = end_idx
                next_end = min(next_start + overlap, total_images)
                overlap_with_next = len(set(partition_images) & set(image_names[next_start:next_end]))
            
            partitions.append(
                PartitionDefinition(
                    index=partition_index,
                    image_names=partition_images,
                    overlap_with_prev=overlap_with_prev,
                    overlap_with_next=overlap_with_next,
                )
            )
            
            # Move to next partition (with overlap)
            if end_idx >= total_images:
                break
            start_idx = end_idx - overlap
            partition_index += 1
        
        return partitions
    
    @staticmethod
    async def preview_partitions(
        block_id: str,
        partition_size: int = 1000,
        overlap: int = 150,
    ) -> List[Dict[str, Any]]:
        """Preview partitions without saving to database.
        
        Args:
            block_id: Block ID
            partition_size: Number of images per partition
            overlap: Overlap between partitions
            
        Returns:
            List of partition dictionaries (for preview)
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Block).where(Block.id == block_id))
            block = result.scalar_one_or_none()
            if not block:
                raise ValueError(f"Block not found: {block_id}")
            
            image_names = PartitionService.get_image_list(block)
            partitions = PartitionService.build_partitions_by_name_with_overlap(
                image_names,
                partition_size=partition_size,
                overlap=overlap,
            )
            
            return [p.to_dict() for p in partitions]
    
    @staticmethod
    async def save_partitions(
        block_id: str,
        partitions: List[PartitionDefinition],
        partition_strategy: str = "name_range_with_overlap",
        partition_params: Optional[Dict[str, Any]] = None,
        sfm_pipeline_mode: str = "global_feat_match",
        merge_strategy: str = "sim3_keep_one",
    ) -> List[BlockPartition]:
        """Save partition definitions to database.
        
        Args:
            block_id: Block ID
            partitions: List of PartitionDefinition objects
            partition_strategy: Strategy identifier
            partition_params: Strategy-specific parameters
            sfm_pipeline_mode: SfM pipeline mode
            merge_strategy: Merge strategy
            
        Returns:
            List of saved BlockPartition instances
        """
        async with AsyncSessionLocal() as db:
            # Update block partition settings
            result = await db.execute(select(Block).where(Block.id == block_id))
            block = result.scalar_one_or_none()
            if not block:
                raise ValueError(f"Block not found: {block_id}")
            
            block.partition_enabled = True
            block.partition_strategy = partition_strategy
            block.partition_params = partition_params or {}
            block.sfm_pipeline_mode = sfm_pipeline_mode
            block.merge_strategy = merge_strategy
            
            # Delete existing partitions for this block
            result_partitions = await db.execute(
                select(BlockPartition).where(BlockPartition.block_id == block_id)
            )
            existing = result_partitions.scalars().all()
            for ep in existing:
                await db.delete(ep)
            
            # Create new partition records
            saved_partitions = []
            for p in partitions:
                bp = BlockPartition(
                    block_id=block_id,
                    index=p.index,
                    name=p.name,
                    image_start_name=p.image_start_name,
                    image_end_name=p.image_end_name,
                    image_count=p.image_count,
                    overlap_with_prev=p.overlap_with_prev,
                    overlap_with_next=p.overlap_with_next,
                    status="PENDING",
                    progress=0.0,
                )
                db.add(bp)
                saved_partitions.append(bp)
            
            await db.commit()
            
            # Refresh to get IDs
            for bp in saved_partitions:
                await db.refresh(bp)
            
            return saved_partitions
    
    @staticmethod
    async def get_partitions(block_id: str, db: AsyncSession) -> List[BlockPartition]:
        """Get all partitions for a block.
        
        Args:
            block_id: Block ID
            db: Database session
            
        Returns:
            List of BlockPartition instances
        """
        result = await db.execute(
            select(BlockPartition)
            .where(BlockPartition.block_id == block_id)
            .order_by(BlockPartition.index)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_partition_image_names(
        block: Block,
        partition: BlockPartition,
    ) -> List[str]:
        """Get list of image names for a specific partition.
        
        Args:
            block: Block instance
            partition: BlockPartition instance
            
        Returns:
            List of image filenames in this partition
        """
        all_images = PartitionService.get_image_list(block)
        if not all_images:
            return []
        
        # Find the range based on start/end names
        try:
            start_idx = all_images.index(partition.image_start_name)
            end_idx = all_images.index(partition.image_end_name) + 1
            return all_images[start_idx:end_idx]
        except ValueError:
            # Fallback: if names not found, return empty (shouldn't happen normally)
            return []

