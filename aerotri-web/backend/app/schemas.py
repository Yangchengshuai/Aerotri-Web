"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .models import BlockStatus, AlgorithmType, MatchingMethod


# ===== Block Schemas =====

class FeatureParams(BaseModel):
    """Feature extraction parameters."""
    use_gpu: Optional[bool] = None
    gpu_index: Optional[int] = None
    max_image_size: Optional[int] = None
    max_num_features: Optional[int] = None
    camera_model: Optional[str] = None
    single_camera: Optional[bool] = None
    
    class Config:
        extra = "allow"  # Allow extra fields for backward compatibility


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
    gs_tiles_status: Optional[str] = None
    gs_tiles_progress: Optional[float] = None
    gs_tiles_current_stage: Optional[str] = None
    gs_tiles_output_path: Optional[str] = None
    gs_tiles_error_message: Optional[str] = None
    gs_tiles_statistics: Optional[Dict[str, Any]] = None
    tiles_status: Optional[str] = None
    tiles_progress: Optional[float] = None
    tiles_current_stage: Optional[str] = None
    tiles_output_path: Optional[str] = None
    tiles_error_message: Optional[str] = None
    tiles_statistics: Optional[Dict[str, Any]] = None
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
    stage: str  # 'dense' | 'mesh' | 'refine' | 'texture'
    type: str  # 'point_cloud' | 'mesh' | 'texture' | 'other'
    name: str
    size_bytes: int
    mtime: datetime
    preview_supported: bool
    download_url: str


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
    stage: str
    type: str  # 'gaussian' | 'other'
    name: str
    size_bytes: int
    mtime: datetime
    preview_supported: bool
    download_url: str


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
    tensorboard_port: Optional[int] = None
    tensorboard_url: Optional[str] = None
    network_gui_port: Optional[int] = None
    network_gui_url: Optional[str] = None


class GSLogResponse(BaseModel):
    """Schema for 3DGS log response."""
    lines: List[str]


class GSTrainParams(BaseModel):
    """Schema for 3DGS training parameters.
    
    Default values match gaussian-splatting source code:
    - Basic: iterations=30000, resolution=-1, data_device='cuda', sh_degree=3
    - Optimization: position_lr_init=0.00016, position_lr_final=0.0000016, etc.
    - Advanced: test_iterations=[7000, 30000], save_iterations=[7000, 30000], etc.
    See arguments/__init__.py and train.py for full defaults.
    """
    # Basic parameters
    iterations: Optional[int] = None  # Default: 30000
    resolution: Optional[int] = None  # Default: -1 (use original resolution)
    data_device: Optional[str] = None  # Default: 'cuda' | 'cpu'
    sh_degree: Optional[int] = None  # Default: 3
    
    # Optimization parameters
    position_lr_init: Optional[float] = None  # Default: 0.00016
    position_lr_final: Optional[float] = None  # Default: 0.0000016
    position_lr_delay_mult: Optional[float] = None  # Default: 0.01
    position_lr_max_steps: Optional[int] = None  # Default: 30000
    feature_lr: Optional[float] = None  # Default: 0.0025
    opacity_lr: Optional[float] = None  # Default: 0.025
    scaling_lr: Optional[float] = None  # Default: 0.005
    rotation_lr: Optional[float] = None  # Default: 0.001
    lambda_dssim: Optional[float] = None  # Default: 0.2
    percent_dense: Optional[float] = None  # Default: 0.01
    densification_interval: Optional[int] = None  # Default: 100
    opacity_reset_interval: Optional[int] = None  # Default: 3000
    densify_from_iter: Optional[int] = None  # Default: 500
    densify_until_iter: Optional[int] = None  # Default: 15000
    densify_grad_threshold: Optional[float] = None  # Default: 0.0002
    
    # Advanced parameters
    white_background: Optional[bool] = None  # Default: False
    random_background: Optional[bool] = None  # Default: False
    test_iterations: Optional[List[int]] = None  # Default: [7000, 30000]
    save_iterations: Optional[List[int]] = None  # Default: [7000, 30000]
    checkpoint_iterations: Optional[List[int]] = None  # Default: []
    quiet: Optional[bool] = None  # Default: False
    disable_viewer: Optional[bool] = None  # Default: False
    
    class Config:
        extra = "allow"  # Allow extra fields for backward compatibility


class GSTrainRequest(BaseModel):
    """Schema for 3DGS training request."""
    gpu_index: int
    train_params: Optional[GSTrainParams] = None


# ===== 3D Tiles Schemas =====

class TilesFileInfo(BaseModel):
    """Schema for 3D Tiles file information."""
    name: str
    type: str  # tileset, tile, glb
    size_bytes: int
    mtime: datetime
    preview_supported: bool
    download_url: str


class TilesFilesResponse(BaseModel):
    """Schema for 3D Tiles files response."""
    files: List[TilesFileInfo]


class TilesStatusResponse(BaseModel):
    """Schema for 3D Tiles status response."""
    block_id: str
    tiles_status: Optional[str] = None
    tiles_progress: Optional[float] = None
    tiles_current_stage: Optional[str] = None
    tiles_output_path: Optional[str] = None
    tiles_error_message: Optional[str] = None
    tiles_statistics: Optional[Dict[str, Any]] = None


class TilesLogResponse(BaseModel):
    """Schema for 3D Tiles log response."""
    block_id: str
    lines: List[str]


class TilesConvertRequest(BaseModel):
    """Schema for 3D Tiles conversion request."""
    keep_glb: Optional[bool] = False  # Whether to keep intermediate GLB file
    optimize: Optional[bool] = False  # Whether to optimize GLB (future use)


class TilesetUrlResponse(BaseModel):
    """Schema for tileset URL response."""
    tileset_url: str


# ===== 3D GS Tiles Schemas =====

class GSTilesFileInfo(BaseModel):
    """Schema for 3D GS Tiles file information."""
    name: str
    type: str  # "tileset", "tile", "glb", etc.
    size_bytes: int
    mtime: datetime
    preview_supported: bool
    download_url: str


class GSTilesFilesResponse(BaseModel):
    """Schema for 3D GS Tiles files response."""
    files: List[GSTilesFileInfo]


class GSTilesStatusResponse(BaseModel):
    """Schema for 3D GS Tiles status response."""
    block_id: str
    gs_tiles_status: Optional[str] = None
    gs_tiles_progress: Optional[float] = None
    gs_tiles_current_stage: Optional[str] = None
    gs_tiles_output_path: Optional[str] = None
    gs_tiles_error_message: Optional[str] = None
    gs_tiles_statistics: Optional[Dict[str, Any]] = None


class GSTilesLogResponse(BaseModel):
    """Schema for 3D GS Tiles log response."""
    block_id: str
    lines: List[str]


class GSTilesConvertRequest(BaseModel):
    """Schema for 3D GS Tiles conversion request."""
    iteration: Optional[int] = None  # Which iteration PLY to convert (e.g., 7000, 15000)
    use_spz: Optional[bool] = False  # Whether to use SPZ compression
    optimize: Optional[bool] = False  # Whether to optimize (future use)


class GSTilesetUrlResponse(BaseModel):
    """Schema for GS tileset URL response."""
    tileset_url: str


# ===== Partition Schemas =====

class PartitionInfo(BaseModel):
    """Schema for partition information."""
    id: Optional[str] = None  # Optional for preview (not saved to DB yet)
    index: int
    name: str
    image_start_name: Optional[str] = None
    image_end_name: Optional[str] = None
    image_count: Optional[int] = None
    overlap_with_prev: Optional[int] = None
    overlap_with_next: Optional[int] = None
    status: Optional[str] = None
    progress: Optional[float] = None
    error_message: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None


class PartitionConfigRequest(BaseModel):
    """Schema for partition configuration request."""
    partition_enabled: bool
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
    partition_size: int
    overlap: int


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
    mean_reprojection_error: float = 0.0


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

