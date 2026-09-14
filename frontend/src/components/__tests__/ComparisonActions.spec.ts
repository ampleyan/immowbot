import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ComparisonActions from '../ComparisonActions.vue'
import { api } from '../../api.js'

const listing = {
  url: 'listing-1',
  source: 'immoweb',
  source_listing_id: '1',
  _list_ids: [],
  _note: '',
  _workflow: { status: 'New' },
}

describe('ComparisonActions', () => {
  it('adds a listing to a list, saves its note, and updates its pipeline status', async () => {
    const addToList = vi.spyOn(api, 'addToList').mockResolvedValue({ ok: true })
    const saveNote = vi.spyOn(api, 'saveNote').mockResolvedValue({ ok: true })
    const saveWorkflow = vi.spyOn(api, 'saveWorkflow').mockResolvedValue({ status: 'Interested' })
    const wrapper = mount(ComparisonActions, { props: { listing, allLists: [{ id: 7, name: 'Shortlist' }] } })

    await wrapper.get('select.list-select').setValue('7')
    await wrapper.get('button.add-list').trigger('click')
    await wrapper.get('textarea').setValue('Call agent')
    await wrapper.get('button.save-note').trigger('click')
    await wrapper.get('select.pipeline-status').setValue('Interested')
    await wrapper.get('button.save-pipeline').trigger('click')
    await flushPromises()

    expect(addToList).toHaveBeenCalledWith(7, 'immoweb', '1')
    expect(saveNote).toHaveBeenCalledWith('immoweb', '1', 'Call agent')
    expect(saveWorkflow).toHaveBeenCalledWith('immoweb', '1', expect.objectContaining({ status: 'Interested' }))
  })
})
