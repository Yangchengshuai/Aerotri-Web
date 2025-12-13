import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BlockCard from '@/components/BlockCard.vue'
import type { Block } from '@/types'

const mockBlock: Block = {
  id: 'test-id',
  name: 'Test Block',
  image_path: '/path/to/images',
  output_path: null,
  status: 'created',
  algorithm: 'glomap',
  matching_method: 'sequential',
  feature_params: null,
  matching_params: null,
  mapper_params: null,
  statistics: null,
  current_stage: null,
  progress: null,
  error_message: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  started_at: null,
  completed_at: null,
}

describe('BlockCard', () => {
  it('renders block name', () => {
    const wrapper = mount(BlockCard, {
      props: { block: mockBlock },
    })
    
    expect(wrapper.text()).toContain('Test Block')
  })

  it('shows correct status for created block', () => {
    const wrapper = mount(BlockCard, {
      props: { block: mockBlock },
    })
    
    expect(wrapper.text()).toContain('待处理')
  })

  it('shows correct status for running block', () => {
    const runningBlock = { ...mockBlock, status: 'running' as const }
    const wrapper = mount(BlockCard, {
      props: { block: runningBlock },
    })
    
    expect(wrapper.text()).toContain('运行中')
  })

  it('shows correct status for completed block', () => {
    const completedBlock = { 
      ...mockBlock, 
      status: 'completed' as const,
      statistics: {
        num_registered_images: 100,
        num_points3d: 50000,
        total_time: 120,
      }
    }
    const wrapper = mount(BlockCard, {
      props: { block: completedBlock },
    })
    
    expect(wrapper.text()).toContain('已完成')
    expect(wrapper.text()).toContain('100')
  })

  it('shows algorithm type', () => {
    const wrapper = mount(BlockCard, {
      props: { block: mockBlock },
    })
    
    expect(wrapper.text()).toContain('GLOMAP')
  })

  it('emits click event', async () => {
    const wrapper = mount(BlockCard, {
      props: { block: mockBlock },
    })
    
    await wrapper.find('.card-content').trigger('click')
    
    expect(wrapper.emitted('click')).toBeTruthy()
  })
})
