/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, nextTick, ref } from 'vue'

import { useMapBulkActions } from '@/maps/home/composables/useMapBulkActions'
import type { MapListView, MapRead } from '@/maps/types/api'

import { aListedMap } from '../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../support/services'

function map(name: string, over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name, alias: name, can_edit: true, ...over })
}

/**
 * The composable on the app's own services, with the two bulk calls and the
 * toasts observed on the real instances.
 */
function setup(maps: MapRead[], viewMode: Ref<MapListView> = ref('table')) {
  const services = fakeMapsServices()
  services.maps.maps.value = maps
  const store = {
    bulkDeleteMaps: vi.spyOn(services.maps, 'bulkDeleteMaps'),
    bulkEditMaps: vi.spyOn(services.maps, 'bulkEditMaps')
  }
  const toast = {
    success: vi.spyOn(services.toasts, 'success'),
    error: vi.spyOn(services.toasts, 'error')
  }
  const openSettings = vi.fn()
  const api = runWithServices(services, () =>
    useMapBulkActions({
      filteredMaps: () => maps,
      viewMode: () => viewMode.value,
      openSettings
    })
  )
  return { api, openSettings, viewMode, store, toast }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useMapBulkActions — selection', () => {
  it('toggles a map in and out of the selection', () => {
    const { api } = setup([map('a'), map('b')])
    api.toggleMapSelection('a')
    expect(api.selectedCount.value).toBe(1)
    api.toggleMapSelection('a')
    expect(api.selectedCount.value).toBe(0)
  })

  it('reports allFilteredSelected only when every filtered map is selected', () => {
    const { api } = setup([map('a'), map('b')])
    expect(api.allFilteredSelected.value).toBe(false)
    api.toggleSelectAllFiltered(true)
    expect(api.allFilteredSelected.value).toBe(true)
    expect(api.selectedCount.value).toBe(2)
    api.toggleSelectAllFiltered(false)
    expect(api.allFilteredSelected.value).toBe(false)
  })

  it('is false for an empty map list', () => {
    const { api } = setup([])
    expect(api.allFilteredSelected.value).toBe(false)
  })

  it('clears the selection when switching to cards view', async () => {
    const viewMode = ref<MapListView>('table')
    const { api } = setup([map('a')], viewMode)
    api.toggleMapSelection('a')
    expect(api.selectedCount.value).toBe(1)
    viewMode.value = 'cards'
    await nextTick()
    expect(api.selectedCount.value).toBe(0)
  })
})

describe('useMapBulkActions — bulk delete', () => {
  it('does not open the confirm dialog when nothing is selected', () => {
    const { api } = setup([map('a')])
    api.openBulkDelete()
    expect(api.confirmBulkDelete.value).toBe(false)
  })

  it('keeps the failed maps selected on partial failure and reports it', async () => {
    const { api, store, toast } = setup([map('a'), map('b')])
    store.bulkDeleteMaps.mockResolvedValueOnce({
      deleted: ['a'],
      failed: [{ name: 'b', reason: 'busy' }]
    })
    api.toggleSelectAllFiltered(true)
    await api.doBulkDelete()
    // 'a' deleted, 'b' failed → 'b' stays selected for retry.
    expect(api.selectedCount.value).toBe(1)
    expect(api.selectedMaps.value.has('b')).toBe(true)
    expect(toast.error).toHaveBeenCalled()
    expect(api.confirmBulkDelete.value).toBe(false)
  })

  it('clears the selection and reports success when all delete', async () => {
    const { api, store, toast } = setup([map('a'), map('b')])
    store.bulkDeleteMaps.mockResolvedValueOnce({ deleted: ['a', 'b'], failed: [] })
    api.toggleSelectAllFiltered(true)
    await api.doBulkDelete()
    expect(api.selectedCount.value).toBe(0)
    expect(toast.success).toHaveBeenCalled()
  })
})

describe('useMapBulkActions — bulk edit', () => {
  it('excludes maps the user may not edit from the editable set', () => {
    const { api } = setup([map('rw'), map('ro', { can_edit: false })])
    api.toggleSelectAllFiltered(true)
    expect(api.editableSelectedNames.value).toEqual(['rw'])
  })

  it('errors when the user may edit none of the selected maps', () => {
    const { api, toast } = setup([map('ro', { can_edit: false })])
    api.toggleSelectAllFiltered(true)
    api.openBulkEdit()
    expect(toast.error).toHaveBeenCalled()
    expect(api.showBulkEdit.value).toBe(false)
  })

  it('collapses to the single-map settings modal when one editable map is selected', () => {
    const { api, openSettings } = setup([map('only')])
    api.toggleMapSelection('only')
    api.openBulkEdit()
    expect(openSettings).toHaveBeenCalledWith(expect.objectContaining({ name: 'only' }))
    expect(api.showBulkEdit.value).toBe(false)
  })

  it('opens the bulk-edit slide-in for several editable maps', () => {
    const { api } = setup([map('a'), map('b')])
    api.toggleSelectAllFiltered(true)
    api.openBulkEdit()
    expect(api.showBulkEdit.value).toBe(true)
  })

  it('applies edits only to editable targets', async () => {
    const { api, store, toast } = setup([map('rw'), map('ro', { can_edit: false })])
    store.bulkEditMaps.mockResolvedValueOnce({ updated: ['rw'], failed: [] })
    api.toggleSelectAllFiltered(true)
    await api.doBulkEdit({ icon_size: 40 })
    expect(store.bulkEditMaps).toHaveBeenCalledWith(['rw'], { icon_size: 40 })
    expect(toast.success).toHaveBeenCalled()
  })

  it('writes the fields the form shapes differently from the map', async () => {
    const { api, store } = setup([map('rw')])
    store.bulkEditMaps.mockResolvedValueOnce({ updated: ['rw'], failed: [] })
    api.toggleSelectAllFiltered(true)

    await api.doBulkEdit({
      click_action: false,
      rotation_interval: ['every', 5],
      hover_template: ''
    })

    expect(store.bulkEditMaps).toHaveBeenCalledWith(['rw'], {
      click_action: 'none',
      rotation_interval: 5,
      hover_template: null
    })
  })

  it('skips the API call for an empty update set', async () => {
    const { api, store } = setup([map('a')])
    api.toggleMapSelection('a')
    await api.doBulkEdit({})
    expect(store.bulkEditMaps).not.toHaveBeenCalled()
    expect(api.showBulkEdit.value).toBe(false)
  })
})
