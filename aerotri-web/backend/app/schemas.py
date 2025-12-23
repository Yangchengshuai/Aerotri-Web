"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, Field

from .models.block import BlockStatus, AlgorithmType, MatchingMethod


# ============ Feature Extraction Parameters ============
class FeatureParams(BaseModel):
    """Feature extraction parameters."""
    use_gpu: bool = True
    gpu_index: int = 0
    max_image_size: int = 2640
    max_num_features: int = 12000
    camera_model: str = "SIMPLE_RADIAL"
    single_camera: bool = True


# ============ Matching Parameters ============
class MatchingParams(BaseModel):
    """Feature matching parameters."""
    method: MatchingMethod = MatchingMethod.SEQUENTIAL
    overlap: int = 10  # For sequential matching
    use_gpu: bool = True
    gpu_index: int = 0
    # Vocabulary tree matching
    vocab_tree_path: Optional[str] = None
    # Spatial matching key parameters
    spatial_max_num_neighbors: int = 50
    spatial_is_gps: bool = True
    spatial_ignore_z: bool = False


# ============ Mapper Parameters ============
class ColmapMapperParams(BaseModel):
    """COLMAP mapper (incremental SfM) parameters."""
    use_pose_prior: bool = False
    ba_use_gpu: bool = True
    ba_gpu_index: int = 0


class GlomapMapperParams(BaseModel):
    """GLOMAP mapper (global SfM) parameters."""
    use_pose_prior: bool = False
    global_positioning_use_gpu: bool = True
    global_positioning_gpu_index: int = 0
    global_positioning_min_num_images_gpu_solver: int = 50
    bundle_adjustment_use_gpu: bool = True
    bundle_adjustment_gpu_index: int = 0
    bundle_adjustment_min_num_images_gpu_solver: int = 50


class InstantsfmMapperParams(BaseModel):
    """InstantSfM mapper (fast global SfM) parameters."""
    export_txt: bool = True
    disable_depths: bool = False
    manual_config_name: Optional[str] = None
    gpu_index: int = 0  # GPU index to use
    num_iteration_bundle_adjustment: int = 3
    bundle_adjustment_max_iterations: int = 200
    bundle_adjustment_function_tolerance: float = 5e-4
    global_positioning_max_iterations: int = 100
    global_positioning_function_tolerance: float = 5e-4
    min_num_matches: int = 30
    min_triangulation_angle: float = 1.5


# ============ Block Schemas ============
class BlockCreate(BaseModel):
    """Schema for creating a new block."""
    name: str = Field(..., min_length=1, max_length=255)
    image_path: str = Field(..., min_length=1)
    algorithm: AlgorithmType = AlgorithmType.GLOMAP
    matching_method: MatchingMethod = MatchingMethod.SEQUENTIAL
    feature_params: Optional[FeatureParams] = None
    matching_params: Optional[MatchingParams] = None
    mapper_params: Optional[dict] = None  # ColmapMapperParams, GlomapMapperParams, or InstantsfmMapperParams


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
    # Reconstruction (OpenMVS) fields
    recon_status: Optional[str] = None
    recon_progress: Optional[float] = None
    recon_current_stage: Optional[str] = None
    recon_output_path: Optional[str] = None
    recon_error_message: Optional[str] = None
    recon_statistics: Optional[dict] = None
    # 3D Gaussian Splatting (3DGS) fields
    gs_status: Optional[str] = None
    gs_progress: Optional[float] = None
    gs_current_stage: Optional[str] = None
    gs_output_path: Optional[str] = None
    gs_error_message: Optional[str] = None
    gs_statistics: Optional[dict] = None
    # Partitioned SfM fields
    partition_enabled: Optional[bool] = None
    partition_strategy: Optional[str] = None
    partition_params: Optional[dict] = None
    sfm_pipeline_mode: Optional[str] = None
    merge_strategy: Optional[str] = None
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
    # For partition aggregation: unique vs sum across partitions
    num_registered_images_unique: int = 0
    num_registered_images_sum: int = 0
    num_points3d: int = 0
    num_observations: int = 0
    mean_reprojection_error: float = 0.0
    mean_track_length: float = 0.0
    stage_times: dict = Field(default_factory=dict)  # Stage -> elapsed seconds
    algorithm_params: dict = Field(default_factory=dict)


# ============ Reconstruction Schemas ============
class ReconstructRequest(BaseModel):
    """Request payload for starting reconstruction."""

    quality_preset: Literal["fast", "balanced", "high"] = "balanced"


class ReconstructionFileInfo(BaseModel):
    """Information about a reconstruction output file."""

    stage: str  # dense | mesh | refine | texture
    type: str  # point_cloud | mesh | texture | other
    name: str
    size_bytes: int
    mtime: datetime
    preview_supported: bool
    download_url: str


class ReconstructionFilesResponse(BaseModel):
    """List of reconstruction output files."""

    files: List[ReconstructionFileInfo]


class ReconstructionStatusResponse(BaseModel):
    """Reconstruction status for a block."""

    block_id: str
    recon_status: Optional[str]
    recon_progress: Optional[float]
    recon_current_stage: Optional[str]
    recon_output_path: Optional[str]
    recon_error_message: Optional[str]
    recon_statistics: Optional[dict]


class ReconstructionLogResponse(BaseModel):
    """Tail of reconstruction logs for a block."""

    block_id: str
    lines: List[str]


# ============ 3DGS (Gaussian Splatting) Schemas ============
class GSTrainParams(BaseModel):
    """Training parameters for gaussian-splatting (server-side)."""

    iterations: int = Field(7000, ge=1)
    resolution: int = Field(2, ge=1)
    data_device: Literal["cpu", "cuda"] = "cpu"
    sh_degree: int = Field(3, ge=0, le=3)


class GSTrainRequest(BaseModel):
    """Request payload for starting 3DGS training."""

    gpu_index: int = Field(0, ge=0)
    train_params: GSTrainParams = Field(default_factory=GSTrainParams)


class GSFileInfo(BaseModel):
    """Information about a 3DGS output file."""

    stage: str  # model | other
    type: str  # gaussian | other
    name: str
    size_bytes: int
    mtime: datetime
    preview_supported: bool
    download_url: str


class GSFilesResponse(BaseModel):
    """List of 3DGS output files."""

    files: List[GSFileInfo]


class GSStatusResponse(BaseModel):
    """3DGS status for a block."""

    block_id: str
    gs_status: Optional[str]
    gs_progress: Optional[float]
    gs_current_stage: Optional[str]
    gs_output_path: Optional[str]
    gs_error_message: Optional[str]
    gs_statistics: Optional[dict]


class GSLogResponse(BaseModel):
    """Tail of 3DGS training logs for a block."""

    block_id: str
    lines: List[str]


# ============ Partition Schemas ============
class PartitionConfigRequest(BaseModel):
    """Request to configure partitions for a block."""
    partition_enabled: bool = False
    partition_strategy: str = "name_range_with_overlap"
    partition_params: dict = Field(default_factory=lambda: {"partition_size": 1000, "overlap": 150})
    sfm_pipeline_mode: str = "global_feat_match"
    merge_strategy: str = Field(default="sim3_keep_one", pattern="^(rigid_keep_one|sim3_keep_one)$")


class PartitionPreviewRequest(BaseModel):
    """Request to preview partitions without saving."""
    partition_size: int = Field(1000, ge=1)
    overlap: int = Field(150, ge=0)


class PartitionInfo(BaseModel):
    """Partition information."""
    id: Optional[str] = None
    index: int
    name: str
    image_start_name: Optional[str] = None
    image_end_name: Optional[str] = None
    image_count: int
    overlap_with_prev: int = 0
    overlap_with_next: int = 0
    status: Optional[str] = None
    progress: Optional[float] = None
    error_message: Optional[str] = None
    image_names: Optional[List[str]] = None  # Only in preview
    statistics: Optional[dict] = None  # Partition statistics (num_registered_images, num_points3d, etc.)


class PartitionConfigResponse(BaseModel):
    """Partition configuration response."""
    partition_enabled: bool
    partition_strategy: Optional[str] = None
    partition_params: Optional[dict] = None
    sfm_pipeline_mode: Optional[str] = None
    merge_strategy: Optional[str] = None
    partitions: List[PartitionInfo] = Field(default_factory=list)


class PartitionPreviewResponse(BaseModel):
    """Partition preview response."""
    partitions: List[PartitionInfo]
    total_images: int
