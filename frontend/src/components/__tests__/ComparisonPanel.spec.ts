import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ComparisonPanel from '../ComparisonPanel.vue'

describe('ComparisonPanel', () => {
  it('shows purchase, workflow, and commute decision fields', () => {
    const wrapper = mount(ComparisonPanel, {
      props: {
        listings: [{
          url: 'listing-1', postcode: '2018', price: 300000, surface_area: 100, _score: 80,
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
    expect(wrapper.text()).toContain('35 min avg')
    expect(wrapper.text()).toContain('€90.000')
  })
})
