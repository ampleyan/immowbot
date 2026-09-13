import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import DetailPanel from '../DetailPanel.vue'

const listing = {
  url: 'https://example.test/listing/1',
  price: 325000,
  property_type: 'apartment',
  bedrooms: 2,
  surface_area: 92,
  postcode: '2018',
  source: 'immoweb',
  epc_score: 'B',
  _score: 78,
  _components: { price: 28, surface_area: 21, bedrooms: 12, epc: 14, completeness: 3 },
  description: '<p>Bright home</p><br><strong>Near the park</strong>',
  image_url_1: 'https://example.test/one.jpg',
}

describe('DetailPanel', () => {
  it('presents a clear property header and sanitized description', () => {
    const wrapper = mount(DetailPanel, { props: { listing } })

    expect(wrapper.find('.detail-header').text()).toContain('€325.000')
    expect(wrapper.find('.detail-desc').text()).toContain('Bright home Near the park')
    expect(wrapper.find('.detail-desc').text()).not.toContain('<p>')
  })

  it('applies the gallery styling hook to property images', () => {
    const wrapper = mount(DetailPanel, { props: { listing } })

    expect(wrapper.find('.detail-gallery img').attributes('src')).toBe(listing.image_url_1)
  })
})
