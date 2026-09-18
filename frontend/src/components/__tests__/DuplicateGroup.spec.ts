import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DuplicateGroup from '../DuplicateGroup.vue'
import { api } from '../../api.js'

const group = {
  confidence: 'high',
  canonical: { url: 'one', source: 'immoweb', source_listing_id: '1' },
  offers: [
    { url: 'one', source: 'immoweb', source_listing_id: '1', price: 300000, postcode: '2000', surface_area: 90 },
    { url: 'two', source: 'zimmo', source_listing_id: '2', price: 305000, postcode: '2000', surface_area: 90 },
  ],
  signals: [{ source: 'zimmo', signals: ['address', 'coordinates'] }],
}

describe('DuplicateGroup', () => {
  it('renders duplicate offers as property cards and merges into the selected offer', async () => {
    const merge = vi.spyOn(api, 'mergeDuplicates').mockResolvedValue({ ok: true })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = mount(DuplicateGroup, { props: { group, modelValue: '' } })

    expect(wrapper.findAll('.card')).toHaveLength(2)
    expect(wrapper.text()).toContain('Select one offer to keep')
    expect(wrapper.text()).toContain('Why grouped')
    expect(wrapper.text()).toContain('zimmo #2 — Potential duplicate of immoweb #1 because of address, coordinates.')
    expect(wrapper.findAll('.card-checkbox')).toHaveLength(0)
    expect(wrapper.find('button.merge-duplicates').exists()).toBe(false)

    await wrapper.get('input[aria-label="Select zimmo listing to keep"]').setValue(true)
    expect(wrapper.find('button.merge-duplicates').exists()).toBe(true)
    await wrapper.get('button.merge-duplicates').trigger('click')

    expect(merge).toHaveBeenCalledWith({ source: 'zimmo', source_listing_id: '2' }, [
      { source: 'immoweb', source_listing_id: '1' },
    ])
    expect(wrapper.emitted('changed')).toHaveLength(1)
  })
})
