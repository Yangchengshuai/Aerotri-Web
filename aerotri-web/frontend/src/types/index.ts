// Block types
export type BlockStatus = 'created' | 'running' | 'completed' | 'failed' | 'cancelled'
export type AlgorithmType = 'colmap' | 'glomap' | 'instantsfm'
export type MatchingMethod = 'sequential' | 'exhaustive' | 'vocab_tree' | 'spatial'

export interface FeatureParams {
  use_gpu: boolean
  gpu_index: number
  max_image_size: number
  max_num_features: number
  camera_model: string
  single_camera: boolean
}

export interface MatchingParams {
  method: MatchingMethod
  // Sequential matching
  overlap: number
  // Common GPU options
  use_gpu: boolean
  gpu_index: number
  // Vocabulary tree matching
  vocab_tree_path?: string
  // Spatial matching parameters
  spatial_max_num_neighbors?: number
  spatial_is_gps?: boolean
  spatial_ignore_z?: boolean
}

export interface ColmapMapperParams {
  // Whether to use EXIF GPS position priors (pose priors) to accelerate SfM.
  use_pose_prior?: boolean
  ba_use_gpu: boolean
  ba_gpu_index: number
}

export interface GlomapMapperParams {
  // Whether to use EXIF GPS position priors (pose priors) to accelerate SfM.
  use_pose_prior?: boolean
  global_positioning_use_gpu: boolean
  global_positioning_gpu_index: number
  bundle_adjustment_use_gpu: boolean
  bundle_adjustment_gpu_index: number
}

export interface InstantsfmMapperParams {
  export_txt: boolean
  disable_depths: boolean
  manual_config_name: string | null
  gpu_index: number
  num_iteration_bundle_adjustment: number
  bundle_adjustment_max_iterations: number
  bundle_adjustment_function_tolerance: number
  global_positioning_max_iterations: number
  global_positioning_function_tolerance: number
  min_num_matches: number
  min_triangulation_angle: number
}

export interface Block {
  id: string
  name: string
  image_path: string
  output_path: string | null
  status: BlockStatus
  algorithm: AlgorithmType
  matching_method: MatchingMethod
  feature_params: FeatureParams | null
  matching_params: MatchingParams | null
  mapper_params: ColmapMapperParams | GlomapMapperParams | InstantsfmMapperParams | null
  statistics: BlockStatistics | null
  current_stage: string | null
  progress: number | null
  error_message: string | null
  // Reconstruction (OpenMVS) fields
  recon_status?: string | null
  recon_progress?: number | null
  recon_current_stage?: string | null
  recon_output_path?: string | null
  recon_error_message?: string | null
  recon_statistics?: Record<string, unknown> | null
  // 3DGS fields
  gs_status?: string | null
  gs_progress?: number | null
  gs_current_stage?: string | null
  gs_output_path?: string | null
  gs_error_message?: string | null
  gs_statistics?: Record<string, unknown> | null
  // Partition fields
  partition_enabled?: boolean
  current_stage?: string | null
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
}

export interface BlockStatistics {
  num_images?: number
  num_registered_images?: number
  num_registered_images_unique?: number
  num_registered_images_sum?: number
  num_points3d?: number
  num_observations?: number
  mean_reprojection_error?: number
  mean_track_length?: number
  stage_times?: Record<string, number>
  total_time?: number
  algorithm_params?: Record<string, unknown>
}

// Reconstruction types
export interface ReconFileInfo {
  stage: 'dense' | 'mesh' | 'refine' | 'texture'
  type: 'point_cloud' | 'mesh' | 'texture' | 'other'
  name: string
  size_bytes: number
  mtime: string
  preview_supported: boolean
  download_url: string
}

export interface ReconstructionState {
  status: 'NOT_STARTED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  progress: number
  currentStage: string | null
  files: ReconFileInfo[]
}

// 3DGS types
export interface GSFileInfo {
  stage: string
  type: string
  name: string
  size_bytes: number
  mtime: string
  preview_supported: boolean
  download_url: string
}

export interface GSState {
  status: 'NOT_STARTED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  progress: number
  currentStage: string | null
  files: GSFileInfo[]
}

// Image types
export interface ImageInfo {
  name: string
  path: string
  size: number
  width?: number
  height?: number
  thumbnail_url?: string
}

export interface ImageListResponse {
  images: ImageInfo[]
  total: number
  page: number
  page_size: number
}

// Filesystem browsing types
export interface DirectoryEntry {
  name: string
  path: string
  has_subdirs: boolean
  has_images: boolean
}

export interface DirectoryListResponse {
  root: string
  current: string
  parent: string | null
  entries: DirectoryEntry[]
}

// GPU types
export interface GPUInfo {
  index: number
  name: string
  memory_total: number
  memory_used: number
  memory_free: number
  utilization: number
  is_available: boolean
}

// Task types
export interface TaskStatus {
  block_id: string
  status: BlockStatus
  current_stage: string | null
  progress: number
  stage_times: Record<string, number> | null
  log_tail: string[] | null
}

// Result types
export interface CameraInfo {
  image_id: number
  image_name: string
  camera_id: number
  qw: number
  qx: number
  qy: number
  qz: number
  tx: number
  ty: number
  tz: number
  num_points: number
}

export interface Point3D {
  id: number
  x: number
  y: number
  z: number
  r: number
  g: number
  b: number
  error: number
  num_observations: number
}

// Progress WebSocket message
export interface ProgressMessage {
  pipeline?: 'sfm' | 'reconstruction'
  stage: string
  progress: number
  message: string
}
