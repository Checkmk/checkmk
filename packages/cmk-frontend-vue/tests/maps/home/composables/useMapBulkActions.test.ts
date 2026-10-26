/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'

import { useMapBulkActions } from '@/maps/home/composables/useMapBulkActions'
import type { MapRead } from '@/maps/types/api'

import { aListedMap } from '../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../support/services'

function map(name: string, over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name, alias: name, can_edit: true, can_delete: true, ...over })
}

/**
 * The composable on the app's own services, with the two bulk calls and the
 * toasts observed on the real instances.
 */
function setup(maps: MapRead[]) {
  const services = fakeMapsServices()
  services.maps.maps.value = maps
  const store = {
    bulkDeleteMaps: vi.spyOn(services.maps, 'bulkDeleteMaps')
  }
  const toast = {
    success: vi.spyOn(services.toasts, 'success'),
    error: vi.spyOn(services.toasts, 'error')
  }
  const api = runWithServices(services, () => useMapBulkActions({ filteredMaps: () => maps }))
  return { api, store, toast }
}

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

  it('selects all only what may be deleted, since delete is the bulk action', () => {
    const { api } = setup([map('a'), map('demo', { is_builtin: true, can_delete: false })])
    expect(api.selectableCount.value).toBe(1)
    api.toggleSelectAllFiltered(true)
    expect(api.selectedCount.value).toBe(1)
    expect(api.allFilteredSelected.value).toBe(true)
  })

  it('is false for an empty map list', () => {
    const { api } = setup([])
    expect(api.allFilteredSelected.value).toBe(false)
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
