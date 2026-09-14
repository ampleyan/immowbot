import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ComparisonPanel from '../ComparisonPanel.vue'

describe('ComparisonPanel', () => {
  it('shows purchase, workflow, and commute decision fields', () => {
    const wrapper = mount(ComparisonPanel, {
      props: {
        listings: [{
          url: 'https://example.test/listing-1', source: 'immoweb', postcode: '2018', price: 300000, surface_area: 100, _score: 80,
          _workflow: { status: 'Contacted', next_follow_up_date: '2026-09-20' },
          _purchase_estimate: { available: true, required_cash: 90000, estimated_loan: 210000, cash_surplus: 10000 },
          _commute: { available: true, destinations: [{ minutes: 30 }, { minutes: 40 }] },
        }],
      },
    })

    expect(wrapper.text()).toContain('Price / m²')
    expect(wrapper.text()).toContain('€3.000')
    expect(wrapper.text()).toContain('Contacted')
    expect(wrapper.text()).toContain('2026-09-20')
    expect(wrapper.text()).not.toContain('35 min avg')
    expect(wrapper.text()).toContain('€90.000')
  })

  it('renders comparison as a modal with a carousel for each property', async () => {
    const wrapper = mount(ComparisonPanel, {
      props: {
        listings: [
          { url: 'listing-1', postcode: '2018', source: 'Portal', image_url_1: 'one-a.jpg', image_url_2: 'one-b.jpg' },
          { url: 'listing-2', postcode: '2000', source: 'Portal', images: ['two-a.jpg', 'two-b.jpg'] },
        ],
      },
    })

    expect(wrapper.get('[role="dialog"]').attributes('aria-modal')).toBe('true')
    expect(wrapper.findAll('.comparison-carousel')).toHaveLength(2)
    expect(wrapper.find('img[src="one-a.jpg"]').exists()).toBe(true)
    expect(wrapper.find('img[src="two-a.jpg"]').exists()).toBe(true)
    expect(wrapper.get('a.comparison-portal-link').attributes('href')).toBe('listing-1')

    const carousels = wrapper.findAll('.comparison-carousel')
    await carousels[0]!.get('button[aria-label="Next image"]').trigger('click')

    expect(wrapper.find('img[src="one-b.jpg"]').exists()).toBe(true)
  })

  it('emits close from the modal close button', async () => {
    const wrapper = mount(ComparisonPanel, { props: { listings: [{ url: 'listing-1' }, { url: 'listing-2' }] } })

    await wrapper.get('button[aria-label="Close comparison"]').trigger('click')

    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('highlights values that differ between properties', () => {
    const wrapper = mount(ComparisonPanel, {
      props: {
        listings: [
          { url: 'listing-1', price: 300000, postcode: '2000' },
          { url: 'listing-2', price: 325000, postcode: '2000' },
        ],
      },
    })

    const priceRow = wrapper.findAll('tbody tr').find(row => row.find('th').text() === 'Price')
    const postcodeRow = wrapper.findAll('tbody tr').find(row => row.find('th').text() === 'Postcode')
    expect(priceRow).toBeDefined()
    expect(postcodeRow).toBeDefined()
    const priceCells = priceRow!.findAll('td')
    const postcodeCells = postcodeRow!.findAll('td')

    expect(priceCells.every(cell => cell.classes('comparison-difference'))).toBe(true)
    expect(postcodeCells.every(cell => !cell.classes('comparison-difference'))).toBe(true)
  })
})
