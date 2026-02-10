import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Block, ReconFileInfo, ReconstructionState, ReconstructionParams, ReconQualityPreset } from '@/types'
import { blockApi, reconstructionApi } from '@/api'

export const useBlocksStore = defineStore('blocks', () => {
  const blocks = ref<Block[]>([])
  const currentBlock = ref<Block | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const reconstruction = ref<Record<string, ReconstructionState>>({})

  const sortedBlocks = computed(() => {
    return [...blocks.value].sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  })

  async function fetchBlocks() {
    loading.value = true
    error.value = null
    try {
      const response = await blockApi.list()
      // Ensure we have the correct response structure
      if (response.data && response.data.blocks) {
        blocks.value = response.data.blocks
      } else if (Array.isArray(response.data)) {
        // Handle case where API returns array directly
        blocks.value = response.data
      } else {
        console.error('Unexpected API response format:', response.data)
        blocks.value = []
      }
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : 'Failed to fetch blocks'
      error.value = errorMessage
      console.error('Error fetching blocks:', e)
      blocks.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchBlock(id: string) {
    loading.value = true
    error.value = null
    try {
      const response = await blockApi.get(id)
      currentBlock.value = response.data
      // Update in list too
      const index = blocks.value.findIndex(b => b.id === id)
      if (index >= 0) {
        blocks.value[index] = response.data
      }
      return response.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch block'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createBlock(data: {
    name: string
    image_path: string
    algorithm?: string
    matching_method?: string
  }) {
    loading.value = true
    error.value = null
    try {
      const response = await blockApi.create(data)
      blocks.value.unshift(response.data)
      return response.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to create block'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateBlock(id: string, data: Partial<Block>) {
    loading.value = true
    error.value = null
    try {
      const response = await blockApi.update(id, data)
      const index = blocks.value.findIndex(b => b.id === id)
      if (index >= 0) {
        blocks.value[index] = response.data
      }
      if (currentBlock.value?.id === id) {
        currentBlock.value = response.data
      }
      // Sync basic reconstruction status into store
      const b = response.data
      if (b.recon_status) {
        reconstruction.value[b.id] = {
          status: (b.recon_status as ReconstructionState['status']) ?? 'NOT_STARTED',
          progress: b.recon_progress ?? 0,
          currentStage: b.recon_current_stage ?? null,
          files: reconstruction.value[b.id]?.files ?? [],
        }
      }
      return response.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to update block'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteBlock(id: string) {
    loading.value = true
    error.value = null
    try {
      await blockApi.delete(id)
      blocks.value = blocks.value.filter(b => b.id !== id)
      if (currentBlock.value?.id === id) {
        currentBlock.value = null
      }
      delete reconstruction.value[id]
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to delete block'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function resetBlock(id: string) {
    loading.value = true
    error.value = null
    try {
      const response = await blockApi.reset(id)
      // Update in list
      const index = blocks.value.findIndex(b => b.id === id)
      if (index >= 0) {
        blocks.value[index] = response.data
      }
      // Update current block if it matches
      if (currentBlock.value?.id === id) {
        currentBlock.value = response.data
      }
      return response.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to reset block'
      throw e
    } finally {
      loading.value = false
    }
  }

  function setCurrentBlock(block: Block | null) {
    currentBlock.value = block
  }

  async function startReconstruction(
    blockId: string, 
    qualityPreset: ReconQualityPreset = 'balanced',
    customParams?: ReconstructionParams
  ) {
    loading.value = true
    error.value = null
    try {
      await reconstructionApi.start(blockId, qualityPreset, customParams)
      // Initialize local state
      reconstruction.value[blockId] = {
        status: 'RUNNING',
        progress: 0,
        currentStage: 'initializing',
        files: reconstruction.value[blockId]?.files ?? [],
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to start reconstruction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function cancelReconstruction(blockId: string) {
    loading.value = true
    error.value = null
    try {
      await reconstructionApi.cancel(blockId)
      // Optimistically update local state; it will be corrected on next status fetch
      reconstruction.value[blockId] = {
        ...(reconstruction.value[blockId] ?? {
          status: 'NOT_STARTED',
          progress: 0,
          currentStage: null,
          files: [],
        }),
        status: 'CANCELLED',
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to cancel reconstruction'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchReconstructionStatus(blockId: string) {
    try {
      const res = await reconstructionApi.status(blockId)
      const data = res.data
      reconstruction.value[blockId] = {
        status: (data.recon_status as ReconstructionState['status']) ?? 'NOT_STARTED',
        progress: data.recon_progress ?? 0,
        currentStage: data.recon_current_stage,
        files: reconstruction.value[blockId]?.files ?? [],
      }
      // Also patch currentBlock if it matches
      if (currentBlock.value?.id === blockId) {
        currentBlock.value = {
          ...currentBlock.value,
          recon_status: data.recon_status,
          recon_progress: data.recon_progress,
          recon_current_stage: data.recon_current_stage,
          recon_output_path: data.recon_output_path,
          recon_error_message: data.recon_error_message,
          recon_statistics: data.recon_statistics,
        }
      }
    } catch (e) {
      // best-effort; do not rethrow to avoid breaking polling
      console.error(e)
    }
  }

  async function fetchReconstructionFiles(blockId: string) {
    try {
      const res = await reconstructionApi.files(blockId)
      const files = res.data.files as ReconFileInfo[]
      if (!reconstruction.value[blockId]) {
        reconstruction.value[blockId] = {
          status: 'NOT_STARTED',
          progress: 0,
          currentStage: null,
          files,
        }
      } else {
        reconstruction.value[blockId].files = files
      }
    } catch (e) {
      console.error(e)
    }
  }

  const getReconstructionState = (blockId: string) =>
    reconstruction.value[blockId] ??
    ({
      status: 'NOT_STARTED',
      progress: 0,
      currentStage: null,
      files: [],
    } as ReconstructionState)

  return {
    blocks,
    currentBlock,
    loading,
    error,
    sortedBlocks,
    fetchBlocks,
    fetchBlock,
    createBlock,
    updateBlock,
    deleteBlock,
    resetBlock,
    setCurrentBlock,
    reconstruction,
    getReconstructionState,
    startReconstruction,
    cancelReconstruction,
    fetchReconstructionStatus,
    fetchReconstructionFiles,
  }
})
