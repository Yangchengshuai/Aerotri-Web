import axios from 'axios'
import type {
  Block,
  ImageListResponse,
  DirectoryListResponse,
  ImageRootsResponse,
  GPUInfo,
  TaskStatus,
  CameraInfo,
  Point3D,
  BlockStatistics,
  ReconFileInfo,
  GSFileInfo,
  TilesFileInfo,
  ReconstructionParams,
  ReconQualityPreset,
  ReconPresetsResponse,
  ReconParamsSchemaResponse,
} from '@/types'

const apiBase =
  import.meta.env.VITE_API_BASE_URL && import.meta.env.VITE_API_BASE_URL.trim().length > 0
    ? import.meta.env.VITE_API_BASE_URL
    : '/api'

const api = axios.create({
  baseURL: apiBase,
  timeout: 30000,
})

// Block API
export const blockApi = {
  list: () => api.get<{ blocks: Block[], total: number }>('/blocks'),

  get: (id: string) => api.get<Block>(`/blocks/${id}`),

  create: (data: {
    name: string
    image_path: string
    algorithm?: string
    matching_method?: string
    feature_params?: Record<string, unknown>
    matching_params?: Record<string, unknown>
    mapper_params?: Record<string, unknown>
  }) => api.post<Block>('/blocks', data),

  update: (id: string, data: Partial<Block>) => api.patch<Block>(`/blocks/${id}`, data),

  // Reset a failed/completed block to CREATED status for re-running
  reset: (id: string) => api.post<Block>(`/blocks/${id}/reset`),

  delete: (id: string) => api.delete(`/blocks/${id}`),
}

// Image API
export const imageApi = {
  list: (blockId: string, page = 1, pageSize = 50) => 
    api.get<ImageListResponse>(`/blocks/${blockId}/images`, {
      params: { page, page_size: pageSize }
    }),
  
  getThumbnailUrl: (blockId: string, imageName: string, size = 200) =>
    `/api/blocks/${blockId}/images/${encodeURIComponent(imageName)}/thumbnail?size=${size}`,
  
  getImageUrl: (blockId: string, imageName: string) =>
    `/api/blocks/${blockId}/images/${encodeURIComponent(imageName)}`,
  
  delete: (blockId: string, imageName: string) =>
    api.delete(`/blocks/${blockId}/images/${encodeURIComponent(imageName)}`),
}

// GPU API
export const gpuApi = {
  list: () => api.get<{ gpus: GPUInfo[] }>('/gpu/status'),
  
  get: (index: number) => api.get<GPUInfo>(`/gpu/status/${index}`),
}

// Task API
export const taskApi = {
  run: (blockId: string, gpuIndex = 0) =>
    api.post<TaskStatus>(`/blocks/${blockId}/run`, { gpu_index: gpuIndex }),
  
  status: (blockId: string) =>
    api.get<TaskStatus>(`/blocks/${blockId}/status`),
  
  stop: (blockId: string) =>
    api.post<TaskStatus>(`/blocks/${blockId}/stop`),
  
  merge: (blockId: string) =>
    api.post<TaskStatus>(`/blocks/${blockId}/merge`),

  glomapMapperResume: (
    blockId: string,
    payload: {
      gpu_index?: number
      input_colmap_path?: string | null
      glomap_params?: Record<string, unknown> | null
    },
  ) =>
    api.post<TaskStatus>(`/blocks/${blockId}/glomap/mapper_resume`, payload),

  versions: (blockId: string) =>
    api.get<{
      versions: Array<{
        id: string
        name: string
        status: string
        glomap_mode: string | null
        parent_block_id: string | null
        version_index: number | null
        output_path: string | null
        output_colmap_path: string | null
        created_at: string | null
        completed_at: string | null
      }>
    }>(`/blocks/${blockId}/versions`),
}

// Filesystem API
export const filesystemApi = {
  listDirs: (path?: string) =>
    api.get<DirectoryListResponse>('/filesystem/dirs', { params: { path } }),

  // List all configured image root directories
  listRoots: () =>
    api.get<ImageRootsResponse>('/filesystem/roots'),
}


// Result API
export const resultApi = {
  getCameras: (blockId: string) =>
    api.get<CameraInfo[]>(`/blocks/${blockId}/result/cameras`),
  
  // Points payload can be very large (tens of MB). Allow overriding timeout per call.
  getPoints: (blockId: string, limit = 100000, timeout: number = 0) =>
    api.get<{ points: Point3D[], total: number }>(`/blocks/${blockId}/result/points`, {
      params: { limit },
      timeout,
    }),
  
  getStats: (blockId: string) =>
    api.get<BlockStatistics>(`/blocks/${blockId}/result/stats`),
  
  downloadPoints3DPly: (blockId: string) =>
    api.get(`/blocks/${blockId}/result/points3d/ply`, {
      responseType: 'blob',
      // 点云文件可能几十/上百 MB，受网络/浏览器影响下载时间可能超过全局 30s timeout
      // 这里禁用超时，避免前端误报“下载失败”
      timeout: 0,
    }),
}

// Reconstruction API
export const reconstructionApi = {
  // Get available quality presets with their parameters
  getPresets: () =>
    api.get<ReconPresetsResponse>('/reconstruction/presets'),

  // Get parameter schema (ranges, descriptions)
  getParamsSchema: () =>
    api.get<ReconParamsSchemaResponse>('/reconstruction/params-schema'),

  // Start reconstruction with optional custom parameters
  start: (
    blockId: string, 
    qualityPreset: ReconQualityPreset = 'balanced',
    customParams?: ReconstructionParams
  ) =>
    api.post(`/blocks/${blockId}/reconstruct`, {
      quality_preset: qualityPreset,
      custom_params: customParams,
    }),

  status: (blockId: string) =>
    api.get<{
      block_id: string
      recon_status: string | null
      recon_progress: number | null
      recon_current_stage: string | null
      recon_output_path: string | null
      recon_error_message: string | null
      recon_statistics: Record<string, unknown> | null
    }>(`/blocks/${blockId}/reconstruction/status`),

  files: (blockId: string) =>
    api.get<{ files: ReconFileInfo[] }>(`/blocks/${blockId}/reconstruction/files`),

  cancel: (blockId: string) =>
    api.post(`/blocks/${blockId}/reconstruction/cancel`, {}),

  logTail: (blockId: string, lines = 200) =>
    api.get<{ block_id: string; lines: string[] }>(
      `/blocks/${blockId}/reconstruction/log_tail`,
      {
        params: { lines },
      },
    ),
}

// Reconstruction Version API (for comparing different reconstruction parameters)
import type { 
  ReconVersion, 
  ReconVersionListResponse, 
  ReconVersionFilesResponse,
} from '@/types'

export const reconVersionApi = {
  // List all reconstruction versions for a block
  list: (blockId: string) =>
    api.get<ReconVersionListResponse>(`/blocks/${blockId}/recon-versions`),

  // Get a specific version
  get: (blockId: string, versionId: string) =>
    api.get<ReconVersion>(`/blocks/${blockId}/recon-versions/${versionId}`),

  // Create a new reconstruction version
  create: (
    blockId: string,
    payload: {
      quality_preset?: ReconQualityPreset
      custom_params?: ReconstructionParams
      name?: string
    }
  ) =>
    api.post<ReconVersion>(`/blocks/${blockId}/recon-versions`, payload),

  // Delete a version
  delete: (blockId: string, versionId: string) =>
    api.delete(`/blocks/${blockId}/recon-versions/${versionId}`),

  // Cancel a running version
  cancel: (blockId: string, versionId: string) =>
    api.post<ReconVersion>(`/blocks/${blockId}/recon-versions/${versionId}/cancel`),

  // List files for a version
  files: (blockId: string, versionId: string) =>
    api.get<ReconVersionFilesResponse>(`/blocks/${blockId}/recon-versions/${versionId}/files`),

  // Get log tail for a version
  logTail: (blockId: string, versionId: string, lines = 200) =>
    api.get<{ version_id: string; lines: string[] }>(
      `/blocks/${blockId}/recon-versions/${versionId}/log_tail`,
      { params: { lines } }
    ),

  // Get download URL for a version file
  getDownloadUrl: (blockId: string, versionId: string, filePath: string) =>
    `${apiBase}/blocks/${blockId}/recon-versions/${versionId}/download?file=${encodeURIComponent(filePath)}`,
}

// 3DGS API
export const gsApi = {
  train: (
    blockId: string,
    payload: {
      gpu_index: number
      train_params: {
        iterations: number
        resolution: number
        data_device: 'cpu' | 'cuda'
        sh_degree: number
      }
    },
  ) => api.post(`/blocks/${blockId}/gs/train`, payload),

  status: (blockId: string) =>
    api.get<{
      block_id: string
      gs_status: string | null
      gs_progress: number | null
      gs_current_stage: string | null
      gs_output_path: string | null
      gs_error_message: string | null
      gs_statistics: Record<string, unknown> | null
      tensorboard_port: number | null
      tensorboard_url: string | null
    }>(`/blocks/${blockId}/gs/status`),

  cancel: (blockId: string) => api.post(`/blocks/${blockId}/gs/cancel`, {}),

  files: (blockId: string) => api.get<{ files: GSFileInfo[] }>(`/blocks/${blockId}/gs/files`),

  logTail: (blockId: string, lines = 200) =>
    api.get<{ block_id: string; lines: string[] }>(`/blocks/${blockId}/gs/log_tail`, {
      params: { lines },
    }),
}

// 3D GS Tiles API
export const gsTilesApi = {
  convert: (blockId: string, payload: {
    iteration?: number
    use_spz?: boolean
    optimize?: boolean
  }) =>
    api.post<{
      block_id: string
      gs_tiles_status?: string
      gs_tiles_progress?: number
      gs_tiles_current_stage?: string
      gs_tiles_output_path?: string
      gs_tiles_error_message?: string
      gs_tiles_statistics?: Record<string, unknown>
    }>(`/blocks/${blockId}/gs/tiles/convert`, payload),
  
  status: (blockId: string) =>
    api.get<{
      block_id: string
      gs_tiles_status?: string
      gs_tiles_progress?: number
      gs_tiles_current_stage?: string
      gs_tiles_output_path?: string
      gs_tiles_error_message?: string
      gs_tiles_statistics?: Record<string, unknown>
    }>(`/blocks/${blockId}/gs/tiles/status`),
  
  cancel: (blockId: string) =>
    api.post<{
      block_id: string
      gs_tiles_status?: string
      gs_tiles_progress?: number
      gs_tiles_current_stage?: string
      gs_tiles_output_path?: string
      gs_tiles_error_message?: string
      gs_tiles_statistics?: Record<string, unknown>
    }>(`/blocks/${blockId}/gs/tiles/cancel`),
  
  files: (blockId: string) =>
    api.get<{
      files: Array<{
        name: string
        type: string
        size_bytes: number
        mtime: string
        preview_supported: boolean
        download_url: string
      }>
    }>(`/blocks/${blockId}/gs/tiles/files`),
  
  tilesetUrl: (blockId: string) =>
    api.get<{ tileset_url: string }>(`/blocks/${blockId}/gs/tiles/tileset_url`),
  
  logTail: (blockId: string, lines = 200) =>
    api.get<{ block_id: string; lines: string[] }>(`/blocks/${blockId}/gs/tiles/log_tail`, {
      params: { lines },
    }),
}

// 3D Tiles API
export const tilesApi = {
  convert: (
    blockId: string,
    payload: {
      keep_glb?: boolean
      optimize?: boolean
    } = {},
  ) => api.post(`/blocks/${blockId}/tiles/convert`, payload),

  status: (blockId: string) =>
    api.get<{
      block_id: string
      tiles_status: string | null
      tiles_progress: number | null
      tiles_current_stage: string | null
      tiles_output_path: string | null
      tiles_error_message: string | null
      tiles_statistics: Record<string, unknown> | null
    }>(`/blocks/${blockId}/tiles/status`),

  cancel: (blockId: string) => api.post(`/blocks/${blockId}/tiles/cancel`, {}),

  files: (blockId: string) =>
    api.get<{ files: TilesFileInfo[] }>(`/blocks/${blockId}/tiles/files`),

  logTail: (blockId: string, lines = 200) =>
    api.get<{ block_id: string; lines: string[] }>(`/blocks/${blockId}/tiles/log_tail`, {
      params: { lines },
    }),

  tilesetUrl: (blockId: string) =>
    api.get<{ tileset_url: string }>(`/blocks/${blockId}/tiles/tileset_url`),

  // === Version-based 3D Tiles API ===
  versionConvert: (
    blockId: string,
    versionId: string,
    payload: {
      keep_glb?: boolean
      optimize?: boolean
    } = {},
  ) => api.post(`/blocks/${blockId}/recon-versions/${versionId}/tiles/convert`, payload),

  versionStatus: (blockId: string, versionId: string) =>
    api.get<{
      block_id: string
      tiles_status: string | null
      tiles_progress: number | null
      tiles_current_stage: string | null
      tiles_output_path: string | null
      tiles_error_message: string | null
      tiles_statistics: Record<string, unknown> | null
    }>(`/blocks/${blockId}/recon-versions/${versionId}/tiles/status`),

  versionFiles: (blockId: string, versionId: string) =>
    api.get<{ files: TilesFileInfo[] }>(`/blocks/${blockId}/recon-versions/${versionId}/tiles/files`),

  versionTilesetUrl: (blockId: string, versionId: string) =>
    api.get<{ tileset_url: string }>(`/blocks/${blockId}/recon-versions/${versionId}/tiles/tileset_url`),
}

// Queue API
export const queueApi = {
  // Get queue list
  list: () =>
    api.get<{
      items: Array<{
        id: string
        name: string
        algorithm: string
        matching_method: string
        queue_position: number
        queued_at: string
        image_path: string
      }>
      total: number
      running_count: number
      max_concurrent: number
    }>('/queue'),

  // Get queue config
  getConfig: () =>
    api.get<{ max_concurrent: number }>('/queue/config'),

  // Update queue config
  updateConfig: (maxConcurrent: number) =>
    api.put<{ max_concurrent: number }>('/queue/config', { max_concurrent: maxConcurrent }),

  // Enqueue a block
  enqueue: (blockId: string) =>
    api.post<{
      block_id: string
      queue_position: number
      queued_at: string
    }>(`/queue/blocks/${blockId}/enqueue`),

  // Dequeue a block
  dequeue: (blockId: string) =>
    api.post<{
      block_id: string
      status: string
    }>(`/queue/blocks/${blockId}/dequeue`),

  // Move block to top of queue
  moveToTop: (blockId: string) =>
    api.post<{
      block_id: string
      queue_position: number
      queued_at: string
    }>(`/queue/blocks/${blockId}/queue/top`),
}

// Partition API
export const partitionApi = {
  getConfig: (blockId: string) =>
    api.get<{
      partition_enabled: boolean
      partition_strategy: string | null
      partition_params: Record<string, unknown> | null
      sfm_pipeline_mode: string | null
      merge_strategy: string | null
      partitions: Array<{
        id?: string
        index: number
        name: string
        image_start_name: string | null
        image_end_name: string | null
        image_count: number
        overlap_with_prev: number
        overlap_with_next: number
        status: string | null
        progress: number | null
        error_message: string | null
      }>
    }>(`/blocks/${blockId}/partitions/config`),

  updateConfig: (blockId: string, config: {
    partition_enabled: boolean
    partition_strategy?: string
    partition_params?: Record<string, unknown>
    sfm_pipeline_mode?: string
    merge_strategy?: string
  }) =>
    api.put(`/blocks/${blockId}/partitions/config`, config),

  preview: (blockId: string, partitionSize: number, overlap: number) =>
    api.post<{
      partitions: Array<{
        index: number
        name: string
        image_start_name: string | null
        image_end_name: string | null
        image_count: number
        overlap_with_prev: number
        overlap_with_next: number
        image_names?: string[]
      }>
      total_images: number
    }>(`/blocks/${blockId}/partitions/preview`, {
      partition_size: partitionSize,
      overlap,
    }),

  getStatus: (blockId: string) =>
    api.get<{
      partition_enabled: boolean
      partition_strategy: string | null
      partition_params: Record<string, unknown> | null
      sfm_pipeline_mode: string | null
      merge_strategy: string | null
      partitions: Array<{
        id?: string
        index: number
        name: string
        image_start_name: string | null
        image_end_name: string | null
        image_count: number
        overlap_with_prev: number
        overlap_with_next: number
        status: string | null
        progress: number | null
        error_message: string | null
        statistics?: {
          num_registered_images?: number
          num_points3d?: number
          num_observations?: number
          mean_reprojection_error?: number
          mean_track_length?: number
        } | null
      }>
    }>(`/blocks/${blockId}/partitions/status`),

  getPartitionCameras: (blockId: string, partitionIndex: number) =>
    api.get<CameraInfo[]>(`/blocks/${blockId}/partitions/${partitionIndex}/result/cameras`),

  getPartitionPoints: (blockId: string, partitionIndex: number, limit = 100000, timeout: number = 0) =>
    api.get<{ points: Point3D[], total: number }>(`/blocks/${blockId}/partitions/${partitionIndex}/result/points`, {
      params: { limit },
      timeout,
    }),

  getPartitionStats: (blockId: string, partitionIndex: number) =>
    api.get<BlockStatistics>(`/blocks/${blockId}/partitions/${partitionIndex}/result/stats`),

  downloadPartitionPoints3DPly: (blockId: string, partitionIndex: number) =>
    api.get(`/blocks/${blockId}/partitions/${partitionIndex}/result/points3d/ply`, {
      responseType: 'blob',
    }),
}

export default api
