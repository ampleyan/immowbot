import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import HomeView from '../HomeView.vue'
import { api } from '../../api.js'

describe('HomeView', () => {
  it('summarizes triage work and links to the matching review views', async () => {
    vi.setSystemTime(new Date('2026-09-18T10:00:00Z'))
    vi.spyOn(api, 'listings').mockResolvedValue([
      { url: 'new', source: 'immoweb', source_listing_id: '1', _first_seen_at: '2026-09-18T08:00:00Z' },
      { url: 'follow-up', source: 'zimmo', source_listing_id: '2', _workflow: { status: 'Interested', next_follow_up_date: '2026-09-18' } },
      { url: 'reviewed', source: 'realo', source_listing_id: '3', _workflow: { status: 'Contacted' } },
    ])
    vi.spyOn(api, 'getAlerts').mockResolvedValue([
      { id: 1, kind: 'price_reduction', source: 'immoweb', source_listing_id: '1', read_at: null },
    ])

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] },
        },
      },
    })
    await flushPromises()

    expect(wrapper.get('.home-summary-value').text()).toBe('3')
    expect(wrapper.get('.home-summary-label').text()).toBe('active properties')
    expect(wrapper.get('.home-action-new .home-action-label').text()).toBe('New today')
    expect(wrapper.get('.home-action-new .home-action-count').text()).toBe('1')
    expect(wrapper.get('.home-action-changed .home-action-count').text()).toBe('1')
    expect(wrapper.get('.home-action-follow-up .home-action-count').text()).toBe('1')
    expect(wrapper.get('a[href="/active?triage=new"]').text()).toContain('Review new')
    expect(wrapper.get('a[href="/active?triage=changed"]').text()).toContain('Review changes')
    expect(wrapper.get('a[href="/active?triage=follow-up"]').text()).toContain('Open follow-ups')
  })
})
