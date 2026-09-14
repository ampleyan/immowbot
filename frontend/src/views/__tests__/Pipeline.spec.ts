import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Pipeline from '../Pipeline.vue'
import { api } from '../../api.js'

describe('Pipeline', () => {
  it('groups listings into workflow columns', async () => {
    vi.spyOn(api, 'listings').mockResolvedValue([
      { url: 'one', source: 'immoweb', source_listing_id: '1', address: 'Main 1', price: 300000, _workflow: { status: 'Interested' } },
      { url: 'two', source: 'zimmo', source_listing_id: '2', address: 'Park 2', price: 250000, _workflow: { status: 'Offer' } },
    ])

    const wrapper = mount(Pipeline)
    await flushPromises()

    expect(wrapper.find('.pipeline-rule-interested').element.parentElement?.textContent).toContain('1')
    expect(wrapper.find('.pipeline-rule-offer').element.parentElement?.textContent).toContain('1')
    expect(wrapper.text()).toContain('Main 1')
    expect(wrapper.text()).toContain('Park 2')
    expect(wrapper.text()).not.toContain('New')
  })

  it('saves a changed status from a card', async () => {
    vi.spyOn(api, 'listings').mockResolvedValue([
      { url: 'one', source: 'immoweb', source_listing_id: '1', address: 'Main 1', _workflow: { status: 'Interested' } },
    ])
    const saveWorkflow = vi.spyOn(api, 'saveWorkflow').mockResolvedValue({ status: 'Contacted' })
    const wrapper = mount(Pipeline)
    await flushPromises()

    await wrapper.get('.pipeline-card select').setValue('Contacted')
    await flushPromises()

    expect(saveWorkflow).toHaveBeenCalledWith('immoweb', '1', expect.objectContaining({ status: 'Contacted' }))
  })
})
