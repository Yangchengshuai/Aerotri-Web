import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Block } from '@/types'
import { blockApi } from '@/api'

export const useBlocksStore = defineStore('blocks', () => {
  const blocks = ref<Block[]>([])
  const currentBlock = ref<Block | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

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
      blocks.value = response.data.blocks
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch blocks'
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
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to delete block'
      throw e
    } finally {
      loading.value = false
    }
  }

  function setCurrentBlock(block: Block | null) {
    currentBlock.value = block
  }

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
    setCurrentBlock,
  }
})
