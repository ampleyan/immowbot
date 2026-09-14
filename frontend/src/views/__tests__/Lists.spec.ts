import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import Lists from '../Lists.vue'

const items = Array.from({ length: 10 }, (_, index) => ({
  source: 'immoweb',
  source_listing_id: String(index + 1),
  price: 250000 + index,
  property_type: 'apartment',
}))

vi.mock('../../api.js', () => ({
  api: {
    getLists: vi.fn().mockResolvedValue([{ id: 1, name: 'Shortlist', item_count: 10 }]),
    getSmartLists: vi.fn().mockResolvedValue([]),
    getListItems: vi.fn().mockResolvedValue(Array.from({ length: 10 }, (_, index) => ({
      source: 'immoweb',
      source_listing_id: String(index + 1),
      price: 250000 + index,
      property_type: 'apartment',
    }))),
    getSmartListItems: vi.fn(),
    createList: vi.fn(),
    deleteList: vi.fn(),
    removeFromList: vi.fn(),
  },
}))

describe('Lists', () => {
  it('renders every property in an expanded list', async () => {
    const wrapper = mount(Lists)
    await flushPromises()

    await wrapper.find('.list-header').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('.list-property')).toHaveLength(items.length)
  })
})
