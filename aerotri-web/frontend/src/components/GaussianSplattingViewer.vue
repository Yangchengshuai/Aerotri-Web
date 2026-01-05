<template>
  <div class="gaussian-splatting-viewer">
    <div ref="container" class="viewer-container">
      <canvas ref="canvas" class="viewer-canvas"></canvas>
    </div>
    <div v-if="loading" class="loading-overlay">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>{{ loadingText }}</span>
    </div>
    <div v-if="error" class="error-overlay">
      <el-alert :title="error" type="error" :closable="false" />
    </div>
    <div v-if="!webgpuSupported && !error && !loading" class="webgpu-warning">
      <el-alert
        title="WebGPU 不支持"
        type="warning"
        :closable="false"
        description="此查看器需要 WebGPU 支持。请使用 Chrome/Edge 113+ 或 Firefox Nightly。"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps<{
  plyUrl: string
}>()

const container = ref<HTMLElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const loading = ref(false)
const loadingText = ref('加载中...')
const error = ref<string | null>(null)
const webgpuSupported = ref(false)

let visionaryApp: any = null
let renderLoop: any = null

// Check WebGPU support
async function checkWebGPUSupport(): Promise<boolean> {
  if (!('gpu' in navigator)) {
    return false
  }
  try {
    const adapter = await (navigator as any).gpu.requestAdapter()
    return adapter !== null
  } catch {
    return false
  }
}

// Load Visionary library
async function loadVisionary(): Promise<any> {
  return new Promise((resolve, reject) => {
    if ((window as any).VisionaryCore) {
      resolve((window as any).VisionaryCore)
      return
    }

    const script = document.createElement('script')
    script.src = '/visionary/visionary-core.umd.js'
    script.onload = () => {
      if ((window as any).VisionaryCore) {
        resolve((window as any).VisionaryCore)
      } else {
        reject(new Error('VisionaryCore not found after script load'))
      }
    }
    script.onerror = () => {
      reject(new Error('Failed to load Visionary library'))
    }
    document.head.appendChild(script)
  })
}

// Initialize Visionary viewer
async function initViewer() {
  if (!container.value || !canvas.value) {
    return
  }

  try {
    loading.value = true
    error.value = null
    loadingText.value = '检查 WebGPU 支持...'

    // Check WebGPU
    const hasWebGPU = await checkWebGPUSupport()
    webgpuSupported.value = hasWebGPU

    if (!hasWebGPU) {
      error.value = 'WebGPU 不支持，无法加载查看器'
      loading.value = false
      return
    }

    loadingText.value = '加载 Visionary 库...'

    // Load Visionary library
    const VisionaryCore = await loadVisionary()

    loadingText.value = '初始化查看器...'

    // Use Visionary's App class for simpler integration
    // Create a minimal DOM structure for App
    const domElements = {
      canvas: canvas.value,
      noWebGPU: document.createElement('div'),
      fpsEl: null,
      pointCountEl: null,
    }

    // Initialize Visionary App
    const { App } = VisionaryCore
    visionaryApp = new App()
    
    // Manually set canvas
    ;(visionaryApp as any).dom = { canvas: canvas.value, noWebGPU: domElements.noWebGPU }

    loadingText.value = '初始化 WebGPU...'
    await visionaryApp.init()

    loadingText.value = '加载模型...'

    // Load the PLY file using App's loadFile method
    await visionaryApp.loadFilePublic(props.plyUrl, {
      onProgress: (progress: number) => {
        loadingText.value = `加载中... ${Math.round(progress * 100)}%`
      },
    })

    loading.value = false
    loadingText.value = ''
  } catch (err: any) {
    console.error('Visionary viewer error:', err)
    error.value = err.message || '初始化查看器失败'
    loading.value = false
  }
}

// Cleanup
function cleanup() {
  if (renderLoop) {
    cancelAnimationFrame(renderLoop)
    renderLoop = null
  }
  if (visionaryApp && typeof visionaryApp.destroy === 'function') {
    visionaryApp.destroy()
    visionaryApp = null
  }
}

// Watch for URL changes
watch(() => props.plyUrl, () => {
  if (props.plyUrl) {
    cleanup()
    initViewer()
  }
})

onMounted(() => {
  if (props.plyUrl) {
    initViewer()
  }
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.gaussian-splatting-viewer {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
}

.viewer-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.viewer-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 10;
  gap: 12px;
}

.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 10;
}

.webgpu-warning {
  position: absolute;
  top: 20px;
  left: 20px;
  right: 20px;
  z-index: 10;
}
</style>
