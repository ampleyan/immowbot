import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Listings from '../Listings.vue'
import { api } from '../../api.js'

describe('Listings', () => {
  it('keeps under-option listings included by default and exposes a checked filter', async () => {
    localStorage.clear()
    vi.spyOn(api, 'listings').mockResolvedValue([
      { url: 'one', source: 'immoweb', source_listing_id: '1', price: 325000, postcode: '2018', under_option: true },
      { url: 'two', source: 'immoweb', source_listing_id: '2', price: 300000, postcode: '2018', under_option: false },
    ])
    vi.spyOn(api, 'getLists').mockResolvedValue([])
    vi.spyOn(api, 'getAlerts').mockResolvedValue([])

    const wrapper = mount(Listings, {
      props: { collectionState: { alive: false } },
    })
    await flushPromises()

    expect(wrapper.find('.filter-bar-body').exists()).toBe(false)
    expect(wrapper.findAll('.review-results .card')).toHaveLength(2)

    await wrapper.get('.filter-bar-toggle').trigger('click')
    const includeUnderOption = wrapper.get('#include-under-option-filter').element as HTMLInputElement
    expect(includeUnderOption.checked).toBe(true)

    await wrapper.get('#include-under-option-filter').setValue(false)
    expect(wrapper.findAll('.review-results .card')).toHaveLength(1)
  })

  it('defaults Active sorting to the latest updated listing', async () => {
    vi.spyOn(api, 'listings').mockResolvedValue([
      { url: 'one', source: 'immoweb', source_listing_id: '1', price: 325000 },
    ])
    vi.spyOn(api, 'getLists').mockResolvedValue([])
    vi.spyOn(api, 'getAlerts').mockResolvedValue([])

    const wrapper = mount(Listings, {
      props: { collectionState: { alive: false } },
    })
    await flushPromises()

    const select = wrapper.get('#sort-listings').element as HTMLSelectElement
    expect(select.value).toBe('lastUpdated')
  })

  it('opens selected property details in a side drawer', async () => {
    vi.spyOn(api, 'listings').mockResolvedValue([
      { url: 'one', source: 'immoweb', source_listing_id: '1', price: 325000, postcode: '2018' },
    ])
    vi.spyOn(api, 'getLists').mockResolvedValue([])
    vi.spyOn(api, 'getAlerts').mockResolvedValue([])

    const wrapper = mount(Listings, {
      props: { collectionState: { alive: false } },
    })
    await flushPromises()

    await wrapper.get('.card').trigger('click')

    expect(wrapper.get('.property-drawer').text()).toContain('€325.000')
    expect(wrapper.findAll('.property-drawer .modal-close')).toHaveLength(1)

    await wrapper.get('.property-drawer .modal-close').trigger('click')
    expect(wrapper.findAll('.property-drawer')).toHaveLength(0)
  })
})
