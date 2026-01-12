// Block types
export type BlockStatus = 'created' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type AlgorithmType = 'colmap' | 'glomap' | 'instantsfm' | 'openmvg_global'
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
  // Note: COLMAP automatically detects GPS vs Cartesian coordinates from database
  spatial_max_num_neighbors?: number
  spatial_ignore_z?: boolean
}

export interface ColmapMapperParams {
  // Whether to use EXIF GPS position priors (pose priors) to accelerate SfM.
  use_pose_prior?: boolean
  ba_use_gpu: boolean
  ba_gpu_index: number
  // Geo-referencing (EXIF GPS -> UTM -> local ENU + Cesium tileset transform)
  georef_enabled?: boolean
  georef_alignment_max_error?: number
  georef_min_common_images?: number
}

export interface GlomapMapperParams {
  // Whether to use EXIF GPS position priors (pose priors) to accelerate SfM.
  use_pose_prior?: boolean
  global_positioning_use_gpu: boolean
  global_positioning_gpu_index: number
  bundle_adjustment_use_gpu: boolean
  bundle_adjustment_gpu_index: number
  // Skip stage flags for GLOMAP mapper
  skip_preprocessing?: boolean
  skip_view_graph_calibration?: boolean
  skip_relative_pose_estimation?: boolean
  skip_rotation_averaging?: boolean
  skip_track_establishment?: boolean
  skip_global_positioning?: boolean
  skip_bundle_adjustment?: boolean
  skip_retriangulation?: boolean
  skip_pruning?: boolean
  // Iteration parameters
  ba_iteration_num?: number
  retriangulation_iteration_num?: number
  // Track Establishment parameters
  track_establishment_min_num_tracks_per_view?: number
  track_establishment_min_num_view_per_track?: number
  track_establishment_max_num_view_per_track?: number
  track_establishment_max_num_tracks?: number
  // Global Positioning parameters
  global_positioning_optimize_positions?: boolean
  global_positioning_optimize_points?: boolean
  global_positioning_optimize_scales?: boolean
  global_positioning_thres_loss_function?: number
  global_positioning_max_num_iterations?: number
  // Bundle Adjustment parameters
  bundle_adjustment_optimize_rotations?: boolean
  bundle_adjustment_optimize_translation?: boolean
  bundle_adjustment_optimize_intrinsics?: boolean
  bundle_adjustment_optimize_principal_point?: boolean
  bundle_adjustment_optimize_points?: boolean
  bundle_adjustment_thres_loss_function?: number
  bundle_adjustment_max_num_iterations?: number
  // Triangulation parameters
  triangulation_complete_max_reproj_error?: number
  triangulation_merge_max_reproj_error?: number
  triangulation_min_angle?: number
  triangulation_min_num_matches?: number
  // Inlier Thresholds parameters
  thresholds_max_angle_error?: number
  thresholds_max_reprojection_error?: number
  thresholds_min_triangulation_angle?: number
  thresholds_max_epipolar_error_E?: number
  thresholds_max_epipolar_error_F?: number
  thresholds_max_epipolar_error_H?: number
  thresholds_min_inlier_num?: number
  thresholds_min_inlier_ratio?: number
  thresholds_max_rotation_error?: number

  // Geo-referencing (EXIF GPS -> UTM -> local ENU + Cesium tileset transform)
  georef_enabled?: boolean
  georef_alignment_max_error?: number
  georef_min_common_images?: number
}

export interface InstantsfmMapperParams {
  export_txt: boolean
  disable_depths: boolean
  manual_config_name: string | null
  gpu_index: number
  num_iteration_bundle_adjustment: number
  bundle_adjustment_max_iterations: number
  bundle_adjustment_function_tolerance: number
  enable_visualization?: boolean
  visualization_port?: number | null
  global_positioning_max_iterations: number
  global_positioning_function_tolerance: number
  min_num_matches: number
  min_triangulation_angle: number

  // Geo-referencing (EXIF GPS -> UTM -> local ENU + Cesium tileset transform)
  georef_enabled?: boolean
  georef_alignment_max_error?: number
  georef_min_common_images?: number
}

// OpenMVG matching method types (from main_ComputeMatches.cpp)
export type OpenmvgMatchingMethod = 
  | 'AUTO'                    // Auto choice from regions type (default)
  | 'BRUTEFORCEL2'            // L2 BruteForce matching
  | 'HNSWL2'                  // L2 Approximate Matching with HNSW graphs
  | 'HNSWL1'                  // L1 Approximate Matching with HNSW graphs
  | 'CASCADEHASHINGL2'        // L2 Cascade Hashing matching
  | 'FASTCASCADEHASHINGL2'    // L2 Cascade Hashing with precomputed hashed regions (faster, more memory)
  | 'BRUTEFORCEHAMMING'       // BruteForce Hamming matching (for binary descriptors)
  | 'HNSWHAMMING'             // Hamming Approximate Matching with HNSW graphs

// OpenMVG pair generation mode types (from main_PairGenerator.cpp)
export type OpenmvgPairMode = 'EXHAUSTIVE' | 'CONTIGUOUS'

export interface OpenmvgParams {
  camera_model: number  // 1: Pinhole, 2: Pinhole radial 1, 3: Pinhole radial 3, 4: Pinhole brown 2
  focal_length: number  // Default focal length in pixels (e.g., 3000)
  feature_preset: 'NORMAL' | 'HIGH'  // Feature density preset
  geometric_model: 'e' | 'f'  // e: Essential matrix (requires intrinsics), f: Fundamental matrix
  num_threads?: number  // Number of threads for feature extraction (default: auto-detect CPU cores - 1)
  // OpenMVG-specific matching parameters (from main_ComputeMatches.cpp)
  matching_method?: OpenmvgMatchingMethod  // Nearest matching method (default: AUTO)
  ratio?: number  // Distance ratio to discard non-meaningful matches (default: 0.8)
  // OpenMVG-specific pair generation parameters (from main_PairGenerator.cpp)
  pair_mode?: OpenmvgPairMode  // Pair generation mode (default: EXHAUSTIVE)
  contiguous_count?: number  // Number of contiguous links when pair_mode is CONTIGUOUS (e.g., 2 = match 0 with (1,2), 1 with (2,3), ...)
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
  openmvg_params: OpenmvgParams | null
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
  // 3D Tiles fields
  tiles_status?: string | null
  tiles_progress?: number | null
  tiles_current_stage?: string | null
  tiles_output_path?: string | null
  tiles_error_message?: string | null
  tiles_statistics?: Record<string, unknown> | null
  tiles_tileset_url?: string | null
  // Partition fields
  partition_enabled?: boolean
  // Queue fields
  queue_position?: number | null
  queued_at?: string | null
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

// Reconstruction parameter types
export interface DensifyParams {
  resolution_level?: number
  number_views?: number
  number_views_fuse?: number
}

export interface MeshParams {
  decimate?: number
  thickness_factor?: number
  quality_factor?: number
}

export interface RefineParams {
  resolution_level?: number
  max_face_area?: number
  scales?: number
}

export interface TextureParams {
  resolution_level?: number
  min_resolution?: number
}

export interface ReconstructionParams {
  densify?: DensifyParams
  mesh?: MeshParams
  refine?: RefineParams
  texture?: TextureParams
}

export type ReconQualityPreset = 'fast' | 'balanced' | 'high'

export interface ReconPresets {
  [preset: string]: {
    densify: DensifyParams
    mesh: MeshParams
    refine: RefineParams
    texture: TextureParams
  }
}

export interface ParamSchemaMeta {
  type: 'int' | 'float'
  min: number
  max: number
  step?: number
  default: number
  description: string
  label: string
}

export interface ReconParamsSchema {
  densify: Record<string, ParamSchemaMeta>
  mesh: Record<string, ParamSchemaMeta>
  refine: Record<string, ParamSchemaMeta>
  texture: Record<string, ParamSchemaMeta>
}

export interface ReconPresetsResponse {
  presets: ReconPresets
  stage_labels: Record<string, string>
}

export interface ReconParamsSchemaResponse {
  schema: ReconParamsSchema
  stage_labels: Record<string, string>
}

// Reconstruction Version types
export type ReconVersionStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

export interface ReconVersion {
  id: string
  block_id: string
  version_index: number
  name: string
  quality_preset: ReconQualityPreset
  custom_params: ReconstructionParams | null
  merged_params: ReconstructionParams | null
  status: ReconVersionStatus
  progress: number
  current_stage: string | null
  output_path: string | null
  error_message: string | null
  statistics: {
    stage_times?: Record<string, number>
    total_time?: number
    params?: {
      quality_preset: string
      custom_params: ReconstructionParams | null
      merged_params: ReconstructionParams | null
    }
  } | null
  created_at: string | null
  completed_at: string | null
  // 3D Tiles fields
  tiles_status: string | null
  tiles_progress: number
  tiles_current_stage: string | null
  tiles_output_path: string | null
  tiles_error_message: string | null
  tiles_statistics: Record<string, unknown> | null
}

export interface ReconVersionListResponse {
  versions: ReconVersion[]
  total: number
}

export interface ReconVersionFilesResponse {
  version_id: string
  files: ReconFileInfo[]
}

export interface ReconFileInfo {
  stage: string
  type: 'point_cloud' | 'mesh' | 'texture'
  name: string
  size_bytes: number
  mtime: string
  preview_supported: boolean
  download_url: string
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

// 3D Tiles types
export interface TilesFileInfo {
  name: string
  type: 'tileset' | 'tile' | 'glb'
  size_bytes: number
  mtime: string
  preview_supported: boolean
  download_url: string
}

export interface TilesState {
  status: 'NOT_STARTED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  progress: number
  currentStage: string | null
  files: TilesFileInfo[]
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
  x?: number | null
  y?: number | null
  z?: number | null
  mean_reprojection_error?: number
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

// Real-time visualization types
export interface RealtimeUpdate {
  step: number
  stepName: string
  cameras: CameraInfo[]
  points: Point3D[]
  timestamp: number
}
