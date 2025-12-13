import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { GPUInfo } from '@/types'
import { gpuApi } from '@/api'

export const useGPUStore = defineStore('gpu', () => {
  const gpus = ref<GPUInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedGpuIndex = ref(0)

  async function fetchGPUs() {
    loading.value = true
    error.value = null
    try {
      const response = await gpuApi.list()
      gpus.value = response.data.gpus
      // Select first available GPU
      const available = gpus.value.find(g => g.is_available)
      if (available) {
        selectedGpuIndex.value = available.index
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch GPUs'
      gpus.value = []
    } finally {
      loading.value = false
    }
  }

  function selectGPU(index: number) {
    selectedGpuIndex.value = index
  }

  return {
    gpus,
    loading,
    error,
    selectedGpuIndex,
    fetchGPUs,
    selectGPU,
  }
})
