import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { flushPromises } from '@vue/test-utils'
import DetailPanel from '../DetailPanel.vue'
import { api } from '../../api.js'

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
  _components: { price: 28, surface_area: 21, bedrooms: 12, epc: 14, completeness: 3 },
  description_english: '<p>Bright home</p><br><strong>Near the park</strong>',
  image_url_1: 'https://example.test/one.jpg',
  images: ['https://example.test/one.jpg', 'https://example.test/two.jpg'],
  outdoor_garden: true,
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

  it('opens the selected image in a modal', async () => {
    const wrapper = mount(DetailPanel, { props: { listing } })
    await wrapper.find('.detail-gallery img').trigger('click')
    expect(wrapper.find('.image-modal').exists()).toBe(true)
    expect(wrapper.find('.image-modal img').attributes('src')).toBe(listing.images[0])
  })

  it('includes every numbered image in the listing details', async () => {
    const wrapper = mount(DetailPanel, {
      props: {
        listing: {
          ...listing,
          images: ['https://example.test/one.jpg'],
          all_property_details: {
            'Image 3 URL': 'https://example.test/three.jpg',
          },
        },
      },
    })

    expect(wrapper.findAll('.gallery-thumb')).toHaveLength(2)
    await wrapper.findAll('.gallery-thumb')[1]!.trigger('click')
    expect(wrapper.find('.detail-gallery > .gallery-image-button img').attributes('src')).toBe('https://example.test/three.jpg')
  })

  it('logs a contact event and shows it in the timeline', async () => {
    vi.spyOn(api, 'getInteractions').mockResolvedValue([])
    const addInteraction = vi.spyOn(api, 'addInteraction').mockResolvedValue({
      id: 1,
      kind: 'call',
      note: 'Asked about the viewing',
      occurred_at: '2026-09-14T10:00:00+00:00',
      next_follow_up_date: '2026-09-16',
    })
    const wrapper = mount(DetailPanel, { props: { listing } })
    await flushPromises()

    await wrapper.get('select.interaction-kind').setValue('call')
    await wrapper.get('textarea.interaction-note').setValue('Asked about the viewing')
    await wrapper.get('input.interaction-follow-up').setValue('2026-09-16')
    await wrapper.get('button.log-interaction').trigger('click')

    expect(addInteraction).toHaveBeenCalledWith('immoweb', '1', {
      kind: 'call',
      note: 'Asked about the viewing',
      next_follow_up_date: '2026-09-16',
    })
    expect(wrapper.find('.interaction-item').text()).toContain('Asked about the viewing')
  })

  it('shows direct contact actions when agent details are available', async () => {
    vi.spyOn(api, 'getWorkflow').mockResolvedValue({
      status: 'Contacted',
      agent_name: 'Alex',
      agent_phone: '+3212345678',
      agent_email: 'alex@example.test',
    })
    const wrapper = mount(DetailPanel, { props: { listing } })
    await flushPromises()

    expect(wrapper.get('a.contact-phone').attributes('href')).toBe('tel:+3212345678')
    expect(wrapper.get('a.contact-email').attributes('href')).toContain('mailto:alex@example.test?subject=')
    expect(wrapper.get('button.copy-contact').text()).toContain('Copy contact')
  })
})
