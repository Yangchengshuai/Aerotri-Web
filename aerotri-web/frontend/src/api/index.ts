import axios from 'axios'
import type { 
  Block, 
  ImageListResponse, 
  DirectoryListResponse, 
  GPUInfo, 
  TaskStatus,
  CameraInfo,
  Point3D,
  BlockStatistics,
  ReconFileInfo,
  GSFileInfo,
} from '@/types'

const api = axios.create({
  baseURL: '/api',
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
  start: (blockId: string, qualityPreset: 'fast' | 'balanced' | 'high' = 'balanced') =>
    api.post(`/blocks/${blockId}/reconstruct`, {
      quality_preset: qualityPreset,
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
    }>(`/blocks/${blockId}/gs/status`),

  cancel: (blockId: string) => api.post(`/blocks/${blockId}/gs/cancel`, {}),

  files: (blockId: string) => api.get<{ files: GSFileInfo[] }>(`/blocks/${blockId}/gs/files`),

  logTail: (blockId: string, lines = 200) =>
    api.get<{ block_id: string; lines: string[] }>(`/blocks/${blockId}/gs/log_tail`, {
      params: { lines },
    }),
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
