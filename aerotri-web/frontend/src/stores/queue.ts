import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { queueApi } from '@/api'

export interface QueueItem {
  id: string
  name: string
  algorithm: string
  matching_method: string
  queue_position: number
  queued_at: string
  image_path: string
}

export const useQueueStore = defineStore('queue', () => {
  const items = ref<QueueItem[]>([])
  const runningCount = ref(0)
  const maxConcurrent = ref(2)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const sortedItems = computed(() => {
    return [...items.value].sort((a, b) => a.queue_position - b.queue_position)
  })

  const availableSlots = computed(() => {
    return Math.max(0, maxConcurrent.value - runningCount.value)
  })

  async function fetchQueue() {
    loading.value = true
    error.value = null
    try {
      const response = await queueApi.list()
      items.value = response.data.items
      runningCount.value = response.data.running_count
      maxConcurrent.value = response.data.max_concurrent
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch queue'
      console.error('Error fetching queue:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchConfig() {
    try {
      const response = await queueApi.getConfig()
      maxConcurrent.value = response.data.max_concurrent
    } catch (e: unknown) {
      console.error('Error fetching queue config:', e)
    }
  }

  async function updateConfig(newMaxConcurrent: number) {
    try {
      const response = await queueApi.updateConfig(newMaxConcurrent)
      maxConcurrent.value = response.data.max_concurrent
      return response.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to update config'
      throw e
    }
  }

  async function enqueue(blockId: string) {
    try {
      const response = await queueApi.enqueue(blockId)
      await fetchQueue()
      return response.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to enqueue'
      throw e
    }
  }

  async function dequeue(blockId: string) {
    try {
      const response = await queueApi.dequeue(blockId)
      await fetchQueue()
      return response.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to dequeue'
      throw e
    }
  }

  async function moveToTop(blockId: string) {
    try {
      const response = await queueApi.moveToTop(blockId)
      await fetchQueue()
      return response.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to move to top'
      throw e
    }
  }

  function isBlockInQueue(blockId: string): boolean {
    return items.value.some(item => item.id === blockId)
  }

  function getBlockQueuePosition(blockId: string): number | null {
    const item = items.value.find(i => i.id === blockId)
    return item ? item.queue_position : null
  }

  return {
    items,
    runningCount,
    maxConcurrent,
    loading,
    error,
    sortedItems,
    availableSlots,
    fetchQueue,
    fetchConfig,
    updateConfig,
    enqueue,
    dequeue,
    moveToTop,
    isBlockInQueue,
    getBlockQueuePosition,
  }
})
