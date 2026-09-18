import { afterEach, describe, expect, it, vi } from 'vitest'
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
  afterEach(() => {
    vi.restoreAllMocks()
  })

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

  it('groups populated normalized facts in the property detail panel', () => {
    const wrapper = mount(DetailPanel, {
      props: {
        listing: {
          ...listing,
          bathrooms: 1,
          floor: 3,
          epc_value: 114,
          epc_certificate_number: '20260901-0000001234-RES-1',
          heating_type: 'Gas',
          renovation_obligation: true,
          renovation_year: 2024,
          monthly_charges: 175,
          cadastral_income: 1200,
          parking: 2,
          terrace: 15,
          garden: true,
          solar_panels: true,
          investment_property: true,
          new_build: true,
          p_score: 'A',
          g_score: 'B',
          source_created_at: '2026-09-01T08:00:00Z',
          source_updated_at: '2026-09-10T08:00:00Z',
          contact_scraped_at: '2026-09-18T08:00:00Z',
        },
      },
    })

    expect(wrapper.text()).toContain('Property')
    expect(wrapper.text()).toContain('Energy')
    expect(wrapper.text()).toContain('Costs & legal')
    expect(wrapper.text()).toContain('Bathrooms')
    expect(wrapper.text()).toContain('1')
    expect(wrapper.text()).toContain('114 kWh/m²/year')
    expect(wrapper.text()).toContain('€175 / month')
    expect(wrapper.text()).toContain('€1.200')
    expect(wrapper.text()).toContain('P-score')
    expect(wrapper.text()).toContain('18.09.2026')
  })

  it('does not render empty normalized facts or contact actions', () => {
    const wrapper = mount(DetailPanel, {
      props: {
        listing: {
          ...listing,
          bathrooms: '',
          floor: null,
          epc_value: null,
          heating_type: ' ',
          monthly_charges: null,
          cadastral_income: '',
          agency_name: '',
          agent_name: '',
          agent_phone: '',
          agent_email: '',
          contact_status: '',
        },
      },
    })

    expect(wrapper.find('.detail-facts').exists()).toBe(false)
    expect(wrapper.find('.contact-actions').exists()).toBe(false)
  })

  it('shows agency details and only the available contact actions', async () => {
    vi.spyOn(api, 'getWorkflow').mockResolvedValue({})
    const wrapper = mount(DetailPanel, {
      props: {
        listing: {
          ...listing,
          agency_name: 'Example Realty',
          agency_address: 'Main Street 12, 2000 Antwerp',
          agency_url: 'https://agency.example.test',
          agent_name: 'Alex',
          agent_phone: '+3212345678',
          contact_status: 'available',
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('a.agency-website').attributes('href')).toBe('https://agency.example.test')
    expect(wrapper.find('a.contact-phone').exists()).toBe(true)
    expect(wrapper.find('a.contact-email').exists()).toBe(false)
    expect(wrapper.find('button.copy-contact').exists()).toBe(true)
  })

  it.each([
    ['available', 'Contact available'],
    ['unavailable', 'Contact unavailable'],
    ['requires_login', 'Requires login'],
    ['reveal_failed', 'Contact reveal failed'],
  ])('shows %s contact status', (status, label) => {
    const wrapper = mount(DetailPanel, {
      props: { listing: { ...listing, contact_status: status } },
    })

    expect(wrapper.find('.contact-status').text()).toBe(label)
  })
})
