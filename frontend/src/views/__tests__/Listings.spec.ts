import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Listings from '../Listings.vue'
import { api } from '../../api.js'

describe('Listings', () => {
  it('defaults Active sorting to the latest updated listing', async () => {
    vi.spyOn(api, 'listings').mockResolvedValue([])
    vi.spyOn(api, 'getLists').mockResolvedValue([])
    vi.spyOn(api, 'getAlerts').mockResolvedValue([])

    const wrapper = mount(Listings, {
      props: { collectionState: { alive: false } },
    })
    await flushPromises()

    expect(wrapper.get('#sort-listings').element.value).toBe('lastUpdated')
  })
})
