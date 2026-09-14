import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MultiSelectChips from '../MultiSelectChips.vue'

describe('MultiSelectChips', () => {
  it('selects options and removes them from chips', async () => {
    const wrapper = mount(MultiSelectChips, { props: { modelValue: ['immoweb'], options: ['immoweb', 'zimmo'] } })

    await wrapper.get('.chip-select-input').trigger('click')
    await wrapper.get('[role="option"]:nth-child(2)').trigger('click')
    const selectedEvents = wrapper.emitted('update:modelValue') || []
    expect(selectedEvents[selectedEvents.length - 1]?.[0]).toEqual(['immoweb', 'zimmo'])

    await wrapper.get('.filter-chip').trigger('click')
    const removedEvents = wrapper.emitted('update:modelValue') || []
    expect(removedEvents[removedEvents.length - 1]?.[0]).toEqual([])
  })
})
