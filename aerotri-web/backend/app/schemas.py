"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .models import BlockStatus, AlgorithmType, MatchingMethod


# ===== Block Schemas =====

class FeatureParams(BaseModel):
    """Feature extraction parameters."""
    pass  # Can be extended with specific feature params


class MatchingParams(BaseModel):
    """Feature matching parameters."""
    method: Optional[str] = None
    # Sequential matching
    overlap: Optional[int] = None
    # Common GPU options
    use_gpu: Optional[bool] = None
    gpu_index: Optional[int] = None
    # Vocabulary tree matching
    vocab_tree_path: Optional[str] = None
    # Spatial matching parameters
    spatial_max_num_neighbors: Optional[int] = None
    spatial_ignore_z: Optional[bool] = None
    
    class Config:
        extra = "allow"  # Allow extra fields for backward compatibility


class BlockCreate(BaseModel):
    """Schema for creating a new block."""
    name: str
    image_path: str
    algorithm: AlgorithmType = AlgorithmType.GLOMAP
    matching_method: MatchingMethod = MatchingMethod.SEQUENTIAL
    feature_params: Optional[FeatureParams] = None
    matching_params: Optional[MatchingParams] = None
    mapper_params: Optional[Dict[str, Any]] = None


class BlockUpdate(BaseModel):
    """Schema for updating a block."""
    name: Optional[str] = None
    algorithm: Optional[AlgorithmType] = None
    matching_method: Optional[MatchingMethod] = None
    feature_params: Optional[FeatureParams] = None
    matching_params: Optional[MatchingParams] = None
    mapper_params: Optional[Dict[str, Any]] = None


class BlockResponse(BaseModel):
    """Schema for block response."""
    id: str
    name: str
    image_path: str
    source_image_path: Optional[str] = None
    working_image_path: Optional[str] = None
    output_path: Optional[str] = None
    status: BlockStatus
    algorithm: AlgorithmType
    matching_method: MatchingMethod
    feature_params: Optional[Dict[str, Any]] = None
    matching_params: Optional[Dict[str, Any]] = None
    mapper_params: Optional[Dict[str, Any]] = None
    glomap_mode: Optional[str] = None
    parent_block_id: Optional[str] = None
    input_colmap_path: Optional[str] = None
    output_colmap_path: Optional[str] = None
    version_index: Optional[int] = None
    glomap_params: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None
    current_stage: Optional[str] = None
    current_detail: Optional[str] = None
    progress: Optional[float] = None
    error_message: Optional[str] = None
    recon_status: Optional[str] = None
    recon_progress: Optional[float] = None
    recon_current_stage: Optional[str] = None
    recon_output_path: Optional[str] = None
    recon_error_message: Optional[str] = None
    recon_statistics: Optional[Dict[str, Any]] = None
    gs_status: Optional[str] = None
    gs_progress: Optional[float] = None
    gs_current_stage: Optional[str] = None
    gs_output_path: Optional[str] = None
    gs_error_message: Optional[str] = None
    gs_statistics: Optional[Dict[str, Any]] = None
    partition_enabled: Optional[bool] = False
    partition_strategy: Optional[str] = None
    partition_params: Optional[Dict[str, Any]] = None
    sfm_pipeline_mode: Optional[str] = None
    merge_strategy: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlockListResponse(BaseModel):
    """Schema for block list response."""
    blocks: List[BlockResponse]
    total: int


# ===== Task Schemas =====

class TaskSubmit(BaseModel):
    """Schema for submitting a task."""
    gpu_index: Optional[int] = None


class TaskStatus(BaseModel):
    """Schema for task status."""
    block_id: str
    status: BlockStatus
    current_stage: Optional[str] = None
    progress: float
    stage_times: Optional[Dict[str, float]] = None
    log_tail: Optional[List[str]] = None


class GlomapResumeRequest(BaseModel):
    """Schema for GLOMAP mapper_resume request."""
    input_colmap_path: Optional[str] = None
    gpu_index: Optional[int] = None
    glomap_params: Optional[Dict[str, Any]] = None


# ===== Reconstruction Schemas =====

class ReconstructRequest(BaseModel):
    """Schema for reconstruction request."""
    quality_preset: Optional[str] = "medium"  # low, medium, high


class ReconstructionFileInfo(BaseModel):
    """Schema for reconstruction file information."""
    name: str
    path: str
    size: int
    stage: Optional[str] = None


class ReconstructionFilesResponse(BaseModel):
    """Schema for reconstruction files response."""
    files: List[ReconstructionFileInfo]


class ReconstructionStatusResponse(BaseModel):
    """Schema for reconstruction status response."""
    block_id: str
    recon_status: Optional[str] = None
    recon_progress: Optional[float] = None
    recon_current_stage: Optional[str] = None
    recon_output_path: Optional[str] = None
    recon_error_message: Optional[str] = None
    recon_statistics: Optional[Dict[str, Any]] = None


class ReconstructionLogResponse(BaseModel):
    """Schema for reconstruction log response."""
    lines: List[str]


# ===== 3DGS Schemas =====

class GSFileInfo(BaseModel):
    """Schema for 3DGS file information."""
    name: str
    path: str
    size: int
    stage: Optional[str] = None


class GSFilesResponse(BaseModel):
    """Schema for 3DGS files response."""
    files: List[GSFileInfo]


class GSStatusResponse(BaseModel):
    """Schema for 3DGS status response."""
    block_id: str
    gs_status: Optional[str] = None
    gs_progress: Optional[float] = None
    gs_current_stage: Optional[str] = None
    gs_output_path: Optional[str] = None
    gs_error_message: Optional[str] = None
    gs_statistics: Optional[Dict[str, Any]] = None


class GSLogResponse(BaseModel):
    """Schema for 3DGS log response."""
    lines: List[str]


class GSTrainParams(BaseModel):
    """Schema for 3DGS training parameters."""
    iterations: Optional[int] = None
    resolution: Optional[int] = None
    # Add more params as needed


class GSTrainRequest(BaseModel):
    """Schema for 3DGS training request."""
    gpu_index: int
    train_params: Optional[GSTrainParams] = None


# ===== Partition Schemas =====

class PartitionInfo(BaseModel):
    """Schema for partition information."""
    id: str
    index: int
    name: str
    image_start_name: Optional[str] = None
    image_end_name: Optional[str] = None
    image_count: Optional[int] = None
    status: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None


class PartitionConfigRequest(BaseModel):
    """Schema for partition configuration request."""
    partition_strategy: str
    partition_params: Dict[str, Any]
    sfm_pipeline_mode: Optional[str] = None
    merge_strategy: Optional[str] = None


class PartitionConfigResponse(BaseModel):
    """Schema for partition configuration response."""
    partition_enabled: bool
    partition_strategy: Optional[str] = None
    partition_params: Optional[Dict[str, Any]] = None
    sfm_pipeline_mode: Optional[str] = None
    merge_strategy: Optional[str] = None
    partitions: List[PartitionInfo]


class PartitionPreviewRequest(BaseModel):
    """Schema for partition preview request."""
    partition_strategy: str
    partition_params: Dict[str, Any]


class PartitionPreviewResponse(BaseModel):
    """Schema for partition preview response."""
    partitions: List[PartitionInfo]
    total_images: int


# ===== Result Schemas =====

class CameraInfo(BaseModel):
    """Schema for camera information."""
    image_id: int
    image_name: str
    qw: float
    qx: float
    qy: float
    qz: float
    tx: float
    ty: float
    tz: float
    camera_id: int
    num_points: int
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None


class Point3D(BaseModel):
    """Schema for 3D point."""
    id: int
    x: float
    y: float
    z: float
    r: int
    g: int
    b: int
    error: Optional[float] = None


class ReconstructionStats(BaseModel):
    """Schema for reconstruction statistics."""
    num_images: int = 0
    num_registered_images: int = 0
    num_registered_images_unique: Optional[int] = None
    num_registered_images_sum: Optional[int] = None
    num_points3d: int = 0
    num_observations: int = 0
    mean_reprojection_error: float = 0.0
    mean_track_length: float = 0.0
    stage_times: Optional[Dict[str, float]] = None
    algorithm_params: Optional[Dict[str, Any]] = None


# ===== Image Schemas =====

class ImageInfo(BaseModel):
    """Schema for image information."""
    name: str
    path: str
    size: int
    thumbnail_url: str


class ImageListResponse(BaseModel):
    """Schema for image list response."""
    images: List[ImageInfo]
    total: int
    page: int
    page_size: int


# ===== GPU Schemas =====

class GPUInfo(BaseModel):
    """Schema for GPU information."""
    index: int
    name: str
    memory_total: int  # MB
    memory_used: int  # MB
    memory_free: int  # MB
    utilization: int  # percentage
    is_available: bool


class GPUListResponse(BaseModel):
    """Schema for GPU list response."""
    gpus: List[GPUInfo]

