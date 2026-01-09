"""Block model for aerotriangulation tasks."""
import enum
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Enum, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class BlockStatus(str, enum.Enum):
    """Block processing status."""
    CREATED = "created"
    QUEUED = "queued"  # Waiting in queue for execution
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AlgorithmType(str, enum.Enum):
    """Algorithm type for mapping."""
    COLMAP = "colmap"  # Incremental SfM
    GLOMAP = "glomap"  # Global SfM
    INSTANTSFM = "instantsfm"  # InstantSfM (Fast Global SfM)
    OPENMVG_GLOBAL = "openmvg_global"  # openMVG Global SfM (CPU-based)


class GlomapMode(str, enum.Enum):
    """GLOMAP running mode."""

    MAPPER = "mapper"  # From database & images
    MAPPER_RESUME = "mapper_resume"  # From existing COLMAP sparse model


class MatchingMethod(str, enum.Enum):
    """Feature matching method."""
    SEQUENTIAL = "sequential"
    EXHAUSTIVE = "exhaustive"
    VOCAB_TREE = "vocab_tree"
    SPATIAL = "spatial"


class Block(Base):
    """Block represents an aerotriangulation project/task."""
    
    __tablename__ = "blocks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # User-provided source directory (never mutate files here)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    # Explicit source path (kept for clarity / future compatibility)
    source_image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Per-block working directory (symlinks/hardlinks), safe to delete inside
    working_image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[BlockStatus] = mapped_column(
        Enum(BlockStatus), 
        default=BlockStatus.CREATED,
        nullable=False
    )
    
    # Algorithm settings
    algorithm: Mapped[AlgorithmType] = mapped_column(
        Enum(AlgorithmType),
        default=AlgorithmType.GLOMAP,
        nullable=False
    )
    matching_method: Mapped[MatchingMethod] = mapped_column(
        Enum(MatchingMethod),
        default=MatchingMethod.SEQUENTIAL,
        nullable=False
    )
    
    # Parameters stored as JSON
    feature_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    matching_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    mapper_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # GLOMAP-specific fields (for mapper vs mapper_resume and versioning)
    glomap_mode: Mapped[Optional[GlomapMode]] = mapped_column(
        Enum(GlomapMode),
        nullable=True,
    )
    # Parent block for resume/optimization tasks (e.g. mapper_resume versions)
    parent_block_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )
    # Explicit COLMAP-style input/output paths for optimization runs
    input_colmap_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_colmap_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Version index within a family (V0 = original, V1 = first resume, ...)
    version_index: Mapped[Optional[int]] = mapped_column(nullable=True)
    # Raw GLOMAP parameters snapshot (especially for mapper_resume)
    glomap_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # openMVG-specific parameters snapshot (for GlobalSfM runs)
    openmvg_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Processing statistics
    statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Current processing stage and progress
    current_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # More granular stage (parsed from logs), optional
    current_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[Optional[float]] = mapped_column(nullable=True, default=0.0)
    
    # Error message if failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ====== Reconstruction (OpenMVS) fields ======
    # Status of reconstruction pipeline (OpenMVS)
    recon_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        default="NOT_STARTED",
    )
    # Overall reconstruction progress (0-100)
    recon_progress: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        default=0.0,
    )
    # Current coarse reconstruction stage, e.g. undistort/convert/densify/mesh/refine/texture/completed
    recon_current_stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    # Root output path for reconstruction artifacts (e.g. <output_path>/recon)
    recon_output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Human-readable error message for reconstruction failures
    recon_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON statistics for reconstruction (stage times, params, etc.)
    recon_statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # ====== 3D Gaussian Splatting (3DGS) fields ======
    # Status of 3DGS training pipeline
    gs_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        default="NOT_STARTED",
    )
    # Overall 3DGS training progress (0-100)
    gs_progress: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        default=0.0,
    )
    # Current coarse 3DGS stage: initializing/dataset_prepare/training/rendering/completed/...
    gs_current_stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    # Root output path for 3DGS artifacts (e.g. <output_path>/gs)
    gs_output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Human-readable error message for 3DGS failures
    gs_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON statistics for 3DGS (stage times, params, iterations, etc.)
    gs_statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # ====== 3D GS Tiles Conversion fields ======
    # Status of 3D GS PLY to 3D Tiles conversion pipeline
    gs_tiles_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        default="NOT_STARTED",
    )
    # Overall 3D GS Tiles conversion progress (0-100)
    gs_tiles_progress: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        default=0.0,
    )
    # Current coarse 3D GS Tiles stage: ply_to_gltf/gltf_to_tiles/completed/...
    gs_tiles_current_stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    # Root output path for 3D GS Tiles artifacts (e.g. <gs_output_path>/3dtiles)
    gs_tiles_output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Human-readable error message for 3D GS Tiles conversion failures
    gs_tiles_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON statistics for 3D GS Tiles (stage times, file sizes, etc.)
    gs_tiles_statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # ====== 3D Tiles Conversion fields ======
    # Status of 3D Tiles conversion pipeline
    tiles_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        default="NOT_STARTED",
    )
    # Overall 3D Tiles conversion progress (0-100)
    tiles_progress: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        default=0.0,
    )
    # Current coarse 3D Tiles stage: obj_to_glb/glb_to_tiles/completed/...
    tiles_current_stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    # Root output path for 3D Tiles artifacts (e.g. <recon_output_path>/tiles)
    tiles_output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Human-readable error message for 3D Tiles conversion failures
    tiles_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON statistics for 3D Tiles (stage times, file sizes, etc.)
    tiles_statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # ====== Partitioned SfM fields (large-scale datasets) ======
    # Whether partitioned SfM mode is enabled for this block
    partition_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    # Partitioning strategy identifier, e.g. "name_range_with_overlap"
    partition_strategy: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    # JSON blob for strategy-specific params, e.g. {"partition_size": 500, "overlap": 50}
    partition_params: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    # SfM pipeline mode: "default" (single-block), "global_feat_match", "per_partition_full", etc.
    sfm_pipeline_mode: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    # Merge strategy for partition results: "rigid_keep_one", "rigid_optimize", etc.
    merge_strategy: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    
    # ====== Task Queue fields ======
    # Queue position (1-based, lower = higher priority; NULL if not queued)
    queue_position: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        default=None,
    )
    # Timestamp when block was added to queue
    queued_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "name": self.name,
            "image_path": self.image_path,
            "source_image_path": self.source_image_path,
            "working_image_path": self.working_image_path,
            "output_path": self.output_path,
            "status": self.status.value,
            "algorithm": self.algorithm.value,
            "matching_method": self.matching_method.value,
            "feature_params": self.feature_params,
            "matching_params": self.matching_params,
            "mapper_params": self.mapper_params,
            "openmvg_params": self.openmvg_params,
            "glomap_mode": self.glomap_mode.value if self.glomap_mode else None,
            "parent_block_id": self.parent_block_id,
            "input_colmap_path": self.input_colmap_path,
            "output_colmap_path": self.output_colmap_path,
            "version_index": self.version_index,
            "glomap_params": self.glomap_params,
            "statistics": self.statistics,
            "current_stage": self.current_stage,
            "current_detail": self.current_detail,
            "progress": self.progress,
            "error_message": self.error_message,
            "recon_status": self.recon_status,
            "recon_progress": self.recon_progress,
            "recon_current_stage": self.recon_current_stage,
            "recon_output_path": self.recon_output_path,
            "recon_error_message": self.recon_error_message,
            "recon_statistics": self.recon_statistics,
            "gs_status": self.gs_status,
            "gs_progress": self.gs_progress,
            "gs_current_stage": self.gs_current_stage,
            "gs_output_path": self.gs_output_path,
            "gs_error_message": self.gs_error_message,
            "gs_statistics": self.gs_statistics,
            "gs_tiles_status": self.gs_tiles_status,
            "gs_tiles_progress": self.gs_tiles_progress,
            "gs_tiles_current_stage": self.gs_tiles_current_stage,
            "gs_tiles_output_path": self.gs_tiles_output_path,
            "gs_tiles_error_message": self.gs_tiles_error_message,
            "gs_tiles_statistics": self.gs_tiles_statistics,
            "tiles_status": self.tiles_status,
            "tiles_progress": self.tiles_progress,
            "tiles_current_stage": self.tiles_current_stage,
            "tiles_output_path": self.tiles_output_path,
            "tiles_error_message": self.tiles_error_message,
            "tiles_statistics": self.tiles_statistics,
            "partition_enabled": self.partition_enabled,
            "partition_strategy": self.partition_strategy,
            "partition_params": self.partition_params,
            "sfm_pipeline_mode": self.sfm_pipeline_mode,
            "merge_strategy": self.merge_strategy,
            "queue_position": self.queue_position,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
