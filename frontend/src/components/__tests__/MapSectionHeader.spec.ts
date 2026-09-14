import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MapSectionHeader from '../MapSectionHeader.vue'

describe('MapSectionHeader', () => {
  it('starts closed and exposes an accessible toggle', async () => {
    const wrapper = mount(MapSectionHeader, { props: { open: false, mapped: 4, withoutCoordinates: 1 } })
    const button = wrapper.get('button')

    expect(button.attributes('aria-expanded')).toBe('false')
    expect(button.text()).toContain('4 mapped')

    await button.trigger('click')

    expect(wrapper.emitted('toggle')).toHaveLength(1)
  })
})
