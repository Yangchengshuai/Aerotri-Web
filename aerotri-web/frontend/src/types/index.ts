// Block types
export type BlockStatus = 'created' | 'running' | 'completed' | 'failed' | 'cancelled'
export type AlgorithmType = 'colmap' | 'glomap'
export type MatchingMethod = 'sequential' | 'exhaustive' | 'vocab_tree'

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
  overlap: number
  use_gpu: boolean
  gpu_index: number
}

export interface ColmapMapperParams {
  ba_use_gpu: boolean
  ba_gpu_index: number
}

export interface GlomapMapperParams {
  global_positioning_use_gpu: boolean
  global_positioning_gpu_index: number
  global_positioning_min_num_images_gpu_solver: number
  bundle_adjustment_use_gpu: boolean
  bundle_adjustment_gpu_index: number
  bundle_adjustment_min_num_images_gpu_solver: number
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
  mapper_params: ColmapMapperParams | GlomapMapperParams | null
  statistics: BlockStatistics | null
  current_stage: string | null
  progress: number | null
  error_message: string | null
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
}

export interface BlockStatistics {
  num_images?: number
  num_registered_images?: number
  num_points3d?: number
  num_observations?: number
  mean_reprojection_error?: number
  mean_track_length?: number
  stage_times?: Record<string, number>
  total_time?: number
  algorithm_params?: Record<string, unknown>
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
  stage: string
  progress: number
  message: string
}
