import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useBlocksStore } from '@/stores/blocks'

// Mock the API
vi.mock('@/api', () => ({
  blockApi: {
    list: vi.fn().mockResolvedValue({
      data: {
        blocks: [
          { id: '1', name: 'Block 1', status: 'created' },
          { id: '2', name: 'Block 2', status: 'completed' },
        ],
        total: 2,
      },
    }),
    get: vi.fn().mockResolvedValue({
      data: { id: '1', name: 'Block 1', status: 'created' },
    }),
    create: vi.fn().mockResolvedValue({
      data: { id: '3', name: 'New Block', status: 'created' },
    }),
    update: vi.fn().mockResolvedValue({
      data: { id: '1', name: 'Updated Block', status: 'created' },
    }),
    delete: vi.fn().mockResolvedValue({}),
  },
}))

describe('BlocksStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty blocks', () => {
    const store = useBlocksStore()
    
    expect(store.blocks).toEqual([])
    expect(store.currentBlock).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('fetches blocks', async () => {
    const store = useBlocksStore()
    
    await store.fetchBlocks()
    
    expect(store.blocks).toHaveLength(2)
    expect(store.blocks[0].name).toBe('Block 1')
  })

  it('creates a new block', async () => {
    const store = useBlocksStore()
    
    const block = await store.createBlock({
      name: 'New Block',
      image_path: '/path/to/images',
    })
    
    expect(block.name).toBe('New Block')
    expect(store.blocks).toContainEqual(expect.objectContaining({ id: '3' }))
  })

  it('updates a block', async () => {
    const store = useBlocksStore()
    await store.fetchBlocks()
    
    const updated = await store.updateBlock('1', { name: 'Updated Block' })
    
    expect(updated.name).toBe('Updated Block')
  })

  it('deletes a block', async () => {
    const store = useBlocksStore()
    await store.fetchBlocks()
    
    await store.deleteBlock('1')
    
    expect(store.blocks).not.toContainEqual(expect.objectContaining({ id: '1' }))
  })

  it('sorts blocks by creation date', async () => {
    const store = useBlocksStore()
    store.blocks = [
      { id: '1', name: 'Old', created_at: '2024-01-01T00:00:00Z' } as any,
      { id: '2', name: 'New', created_at: '2024-06-01T00:00:00Z' } as any,
    ]
    
    expect(store.sortedBlocks[0].name).toBe('New')
    expect(store.sortedBlocks[1].name).toBe('Old')
  })
})
