import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ListSectionHeader from '../ListSectionHeader.vue'

describe('ListSectionHeader', () => {
  it('exposes an accessible toggle button', async () => {
    const wrapper = mount(ListSectionHeader, {
      props: { name: 'Favorites', count: 3, open: false, controlsId: 'list-1' },
    })
    const button = wrapper.get('button')

    expect(button.attributes('aria-expanded')).toBe('false')
    expect(button.attributes('aria-controls')).toBe('list-1')
    expect(button.text()).toContain('Favorites')
    expect(button.text()).toContain('3 properties')

    await button.trigger('click')

    expect(wrapper.emitted('toggle')).toHaveLength(1)
  })
})
