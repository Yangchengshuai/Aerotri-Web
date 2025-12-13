"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from .models.block import BlockStatus, AlgorithmType, MatchingMethod


# ============ Feature Extraction Parameters ============
class FeatureParams(BaseModel):
    """Feature extraction parameters."""
    use_gpu: bool = True
    gpu_index: int = 0
    max_image_size: int = 2000
    max_num_features: int = 4096
    camera_model: str = "SIMPLE_RADIAL"
    single_camera: bool = True


# ============ Matching Parameters ============
class MatchingParams(BaseModel):
    """Feature matching parameters."""
    method: MatchingMethod = MatchingMethod.SEQUENTIAL
    overlap: int = 20  # For sequential matching
    use_gpu: bool = True
    gpu_index: int = 0


# ============ Mapper Parameters ============
class ColmapMapperParams(BaseModel):
    """COLMAP mapper (incremental SfM) parameters."""
    ba_use_gpu: bool = True
    ba_gpu_index: int = 0


class GlomapMapperParams(BaseModel):
    """GLOMAP mapper (global SfM) parameters."""
    global_positioning_use_gpu: bool = True
    global_positioning_gpu_index: int = 0
    global_positioning_min_num_images_gpu_solver: int = 1
    bundle_adjustment_use_gpu: bool = True
    bundle_adjustment_gpu_index: int = 0
    bundle_adjustment_min_num_images_gpu_solver: int = 1


# ============ Block Schemas ============
class BlockCreate(BaseModel):
    """Schema for creating a new block."""
    name: str = Field(..., min_length=1, max_length=255)
    image_path: str = Field(..., min_length=1)
    algorithm: AlgorithmType = AlgorithmType.GLOMAP
    matching_method: MatchingMethod = MatchingMethod.SEQUENTIAL
    feature_params: Optional[FeatureParams] = None
    matching_params: Optional[MatchingParams] = None
    mapper_params: Optional[dict] = None  # ColmapMapperParams or GlomapMapperParams


class BlockUpdate(BaseModel):
    """Schema for updating a block."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    algorithm: Optional[AlgorithmType] = None
    matching_method: Optional[MatchingMethod] = None
    feature_params: Optional[FeatureParams] = None
    matching_params: Optional[MatchingParams] = None
    mapper_params: Optional[dict] = None


class BlockResponse(BaseModel):
    """Schema for block API response."""
    id: str
    name: str
    image_path: str
    output_path: Optional[str]
    status: BlockStatus
    algorithm: AlgorithmType
    matching_method: MatchingMethod
    feature_params: Optional[dict]
    matching_params: Optional[dict]
    mapper_params: Optional[dict]
    statistics: Optional[dict]
    current_stage: Optional[str]
    progress: Optional[float]
    error_message: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class BlockListResponse(BaseModel):
    """Schema for block list response."""
    blocks: List[BlockResponse]
    total: int


# ============ Image Schemas ============
class ImageInfo(BaseModel):
    """Image information."""
    name: str
    path: str
    size: int  # bytes
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_url: Optional[str] = None


class ImageListResponse(BaseModel):
    """Image list response with pagination."""
    images: List[ImageInfo]
    total: int
    page: int
    page_size: int


# ============ GPU Schemas ============
class GPUInfo(BaseModel):
    """GPU device information."""
    index: int
    name: str
    memory_total: int  # MB
    memory_used: int  # MB
    memory_free: int  # MB
    utilization: int  # percentage
    is_available: bool


class GPUListResponse(BaseModel):
    """GPU list response."""
    gpus: List[GPUInfo]


# ============ Task Schemas ============
class TaskSubmit(BaseModel):
    """Task submission request."""
    gpu_index: int = 0


class TaskStatus(BaseModel):
    """Task status response."""
    block_id: str
    status: BlockStatus
    current_stage: Optional[str]
    progress: float
    stage_times: Optional[dict]  # Stage -> elapsed seconds
    log_tail: Optional[List[str]]  # Last N lines of log


# ============ Result Schemas ============
class CameraInfo(BaseModel):
    """Camera information from reconstruction."""
    image_id: int
    image_name: str
    camera_id: int
    qw: float
    qx: float
    qy: float
    qz: float
    tx: float
    ty: float
    tz: float
    num_points: int


class Point3D(BaseModel):
    """3D point from reconstruction."""
    id: int
    x: float
    y: float
    z: float
    r: int
    g: int
    b: int
    error: float
    num_observations: int


class ReconstructionStats(BaseModel):
    """Reconstruction statistics."""
    num_images: int = 0
    num_registered_images: int = 0
    num_points3d: int = 0
    num_observations: int = 0
    mean_reprojection_error: float = 0.0
    mean_track_length: float = 0.0
    stage_times: dict = Field(default_factory=dict)  # Stage -> elapsed seconds
    algorithm_params: dict = Field(default_factory=dict)
