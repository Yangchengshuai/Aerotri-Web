import { defineStore } from 'pinia'
import type { CameraInfo } from '@/types'

interface CameraSelectionState {
  selectedCameraId: number | null
  selectedImageName: string | null
  selectedCamera: CameraInfo | null
  cameras: CameraInfo[]
  isPanelOpen: boolean
  blockId: string | null
  errorThreshold: number  // 问题相机阈值（像素）
}

export const useCameraSelectionStore = defineStore('cameraSelection', {
  state: (): CameraSelectionState => ({
    selectedCameraId: null,
    selectedImageName: null,
    selectedCamera: null,
    cameras: [],
    isPanelOpen: false,
    blockId: null,
    errorThreshold: 1.0,  // 默认阈值 1.0 px
  }),

  getters: {
    hasSelection: (state) => state.selectedCameraId !== null,
    // 判断相机是否为问题相机（误差 > 阈值）
    isProblemCamera: (state) => (camera: CameraInfo): boolean => {
      return camera.mean_reprojection_error != null && 
             camera.mean_reprojection_error > state.errorThreshold
    },
  },

  actions: {
    setBlockId(blockId: string) {
      this.blockId = blockId
      // Reset selection when block changes
      this.clearSelection()
    },

    setCameras(cameras: CameraInfo[]) {
      this.cameras = cameras
      // If selected camera is no longer in list, clear selection
      if (this.selectedCameraId !== null) {
        const stillExists = cameras.some(cam => cam.image_id === this.selectedCameraId)
        if (!stillExists) {
          this.clearSelection()
        }
      }
    },

    setSelectedCamera(cameraId: number | null) {
      if (cameraId === null) {
        this.clearSelection()
        return
      }

      const camera = this.cameras.find(cam => cam.image_id === cameraId)
      if (camera) {
        this.selectedCameraId = cameraId
        this.selectedImageName = camera.image_name
        this.selectedCamera = camera
        this.isPanelOpen = true
      }
    },

    setSelectedCameraByImageName(imageName: string | null) {
      if (imageName === null) {
        this.clearSelection()
        return
      }

      const camera = this.cameras.find(cam => cam.image_name === imageName)
      if (camera) {
        this.setSelectedCamera(camera.image_id)
      }
    },

    clearSelection() {
      this.selectedCameraId = null
      this.selectedImageName = null
      this.selectedCamera = null
      this.isPanelOpen = false
    },

    togglePanel() {
      this.isPanelOpen = !this.isPanelOpen
    },

    closePanel() {
      this.isPanelOpen = false
    },

    openPanel() {
      if (this.selectedCameraId !== null) {
        this.isPanelOpen = true
      }
    },

    removeCamera(cameraId: number) {
      // Remove from cameras list
      this.cameras = this.cameras.filter(cam => cam.image_id !== cameraId)
      
      // If removed camera was selected, clear selection
      if (this.selectedCameraId === cameraId) {
        this.clearSelection()
      }
    },

    setErrorThreshold(threshold: number) {
      // 限制范围在 0 - 2.0 之间
      this.errorThreshold = Math.max(0, Math.min(2.0, threshold))
    },
  },
})

