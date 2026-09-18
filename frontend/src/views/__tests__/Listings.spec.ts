import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Listings from '../Listings.vue'
import { api } from '../../api.js'

describe('Listings', () => {
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
