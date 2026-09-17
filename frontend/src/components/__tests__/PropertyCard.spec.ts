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
  source_listing_id: '1',
  epc_score: 'B',
  _score: 78,
  _components: {
    price: 28,
    surface_area: 21,
    bedrooms: 12,
    epc: 14,
    completeness: 3,
  },
  description_english: '<p>Bright home</p><br><strong>Near the park</strong>',
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

    expect(wrapper.find('.card-score-summary').text()).toContain('Price 93%')
    expect(wrapper.find('.card-score-summary').text()).toContain('Surface 84%')
    expect(wrapper.find('.card-score-summary').text()).toContain('EPC 70%')
    expect(wrapper.find('.score-highlight-high').text()).toContain('Price 93%')
    expect(wrapper.find('.score-highlight-medium').text()).toContain('EPC 70%')
  })

  it('grades EPC chips by energy rating', () => {
    const wrapper = mount(PropertyCard, { props: { listing: { ...listing, epc_score: 'C' } } })
    expect(wrapper.find('.pill-epc').classes()).toContain('epc-yellow')
  })

  it('shows the source listing id in the overview', () => {
    const wrapper = mount(PropertyCard, { props: { listing } })
    expect(wrapper.find('.card-id').text()).toBe('Listing ID: 1')
  })

  it('shows outdoor features in the overview', () => {
    const wrapper = mount(PropertyCard, {
      props: { listing: { ...listing, outdoor_terrace: true, outdoor_surface: 18, outdoor_garden: true } },
    })

    expect(wrapper.findAll('.pill-outdoor').map(pill => pill.text())).toEqual(['🌿 Terrace 18 m²', '🌿 Garden'])
  })

  it('marks a recently collected listing as new', () => {
    const wrapper = mount(PropertyCard, {
      props: { listing: { ...listing, _first_seen_at: new Date().toISOString() } },
    })

    expect(wrapper.find('.pill-new').text()).toBe('new')
  })

  it('makes an under-option listing unmistakable while keeping it visible', () => {
    const wrapper = mount(PropertyCard, { props: { listing: { ...listing, under_option: true } } })

    expect(wrapper.find('.pill-under-option').text()).toBe('UNDER OPTION')
  })

  it('marks excluded listings with a dimmed card state', () => {
    const wrapper = mount(PropertyCard, {
      props: { listing: { ...listing, _score: null } },
    })

    expect(wrapper.find('.card').classes()).toContain('excluded')
  })

  it('opens details from the row while keeping controls independent', async () => {
    const wrapper = mount(PropertyCard, { props: { listing } })

    await wrapper.find('.card').trigger('click')
    expect(wrapper.emitted('toggle-detail')).toHaveLength(1)

    await wrapper.get('button.list-action').trigger('click')
    expect(wrapper.emitted('toggle-save')).toHaveLength(1)
    expect(wrapper.emitted('toggle-detail')).toHaveLength(1)

    await wrapper.find('input[type="checkbox"]').trigger('click')
    expect(wrapper.emitted('toggle-detail')).toHaveLength(1)
    await wrapper.find('input[type="checkbox"]').trigger('change')
    expect(wrapper.emitted('toggle-select')).toHaveLength(1)
    expect(wrapper.emitted('toggle-detail')).toHaveLength(1)
  })

  it('offers reversible shortlist and reject actions', async () => {
    const wrapper = mount(PropertyCard, { props: { listing } })

    await wrapper.get('button.quick-shortlist').trigger('click')
    await wrapper.get('button.quick-reject').trigger('click')

    expect(wrapper.emitted('quick-status')?.map(event => event[0])).toEqual(['Interested', 'Rejected'])
  })
})
