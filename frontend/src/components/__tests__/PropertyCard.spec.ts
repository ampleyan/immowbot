import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PropertyCard from '../PropertyCard.vue'

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
  _components: {
    price: 28,
    surface_area: 21,
    bedrooms: 12,
    epc: 14,
    completeness: 3,
  },
  description: '<p>Bright home</p><br><strong>Near the park</strong>',
}

describe('PropertyCard', () => {
  it('renders descriptions as readable text without portal markup', () => {
    const wrapper = mount(PropertyCard, { props: { listing } })

    expect(wrapper.find('.card-desc').text()).toContain('Bright home Near the park')
    expect(wrapper.find('.card-desc').text()).not.toContain('<p>')
    expect(wrapper.find('.card-desc').text()).not.toContain('<strong>')
  })

  it('shows the strongest score contributors on the card', () => {
    const wrapper = mount(PropertyCard, { props: { listing } })

    expect(wrapper.find('.card-score-summary').text()).toContain('Price 28/30')
    expect(wrapper.find('.card-score-summary').text()).toContain('Surface 21/25')
    expect(wrapper.find('.card-score-summary').text()).toContain('EPC 14/20')
  })

  it('marks a recently collected listing as new', () => {
    const wrapper = mount(PropertyCard, {
      props: { listing: { ...listing, _first_seen_at: new Date().toISOString() } },
    })

    expect(wrapper.find('.pill-new').text()).toBe('new')
  })

  it('marks excluded listings with a dimmed card state', () => {
    const wrapper = mount(PropertyCard, {
      props: { listing: { ...listing, _score: null } },
    })

    expect(wrapper.find('.card').classes()).toContain('excluded')
  })
})
