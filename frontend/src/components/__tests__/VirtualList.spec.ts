import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import VirtualList from '../VirtualList.vue'

describe('VirtualList', () => {
  it('mounts only the visible window of items', () => {
    const items = Array.from({ length: 100 }, (_, index) => index)
    const wrapper = mount(VirtualList, {
      props: { items, itemHeight: 50, maxHeight: 100 },
      slots: { default: '<span>{{ item }}</span>' },
    })

    expect(wrapper.findAll('.virtual-list-item')).toHaveLength(4)
    expect(wrapper.find('.virtual-list-spacer').attributes('style')).toContain('height: 5000px')
  })

  it('updates the mounted window when scrolling', async () => {
    const items = Array.from({ length: 100 }, (_, index) => index)
    const wrapper = mount(VirtualList, {
      props: { items, itemHeight: 50, maxHeight: 100 },
      slots: { default: '<span>{{ item }}</span>' },
    })
    const viewport = wrapper.find('.virtual-list')
    Object.defineProperty(viewport.element, 'scrollTop', { value: 200, writable: true })

    await viewport.trigger('scroll')

    expect(wrapper.find('.virtual-list-item').text()).toContain('3')
  })
})
