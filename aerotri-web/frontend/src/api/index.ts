import axios from 'axios'
import type { 
  Block, 
  ImageListResponse, 
  GPUInfo, 
  TaskStatus,
  CameraInfo,
  Point3D,
  BlockStatistics
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
}

// Result API
export const resultApi = {
  getCameras: (blockId: string) =>
    api.get<CameraInfo[]>(`/blocks/${blockId}/result/cameras`),
  
  getPoints: (blockId: string, limit = 100000) =>
    api.get<{ points: Point3D[], total: number }>(`/blocks/${blockId}/result/points`, {
      params: { limit }
    }),
  
  getStats: (blockId: string) =>
    api.get<BlockStatistics>(`/blocks/${blockId}/result/stats`),
}

export default api
