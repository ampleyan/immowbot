import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import FollowUpCalendar from '../FollowUpCalendar.vue'

describe('FollowUpCalendar', () => {
  it('places follow-ups on their calendar day and emits selection', async () => {
    const wrapper = mount(FollowUpCalendar, {
      props: {
        month: '2026-09',
        listings: [{ url: 'listing-1', postcode: '2018', _workflow: { next_follow_up_date: '2026-09-14' } }],
      },
    })

    expect(wrapper.find('.follow-up-calendar-title').text()).toContain('September 2026')
    const item = wrapper.get('button')
    expect(item.text()).toBe('2018')

    await item.trigger('click')

    expect(wrapper.emitted('select')).toEqual([['listing-1']])
  })
})
