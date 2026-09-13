import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ListPropertyRow from '../ListPropertyRow.vue'

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
}

describe('ListPropertyRow', () => {
  it('renders a compact property summary and opens the listing', async () => {
    const wrapper = mount(ListPropertyRow, { props: { listing } })

    expect(wrapper.find('.list-property-price').text()).toBe('€325.000')
    expect(wrapper.find('.list-property-specs').text()).toContain('2 bd · 92 m² · 2018')
    expect(wrapper.find('.card').exists()).toBe(false)

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('open')).toHaveLength(1)
  })
})
