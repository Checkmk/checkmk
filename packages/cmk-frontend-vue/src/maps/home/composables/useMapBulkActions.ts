/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import { useMaps, useToast } from '@/maps/services/context'
import { errorText } from '@/maps/shared/errorText'
import { metadataUpdatesFrom } from '@/maps/shared/metadataForm'
import type { MapListView, MapRead } from '@/maps/types/api'

interface MapBulkActionsOptions {
  filteredMaps: () => MapRead[]
  viewMode: () => MapListView
  /**
   * Opens the single-map settings modal. Optional: without it a selection of
   * one goes through the bulk slide-in like any other.
   */
  openSettings?: ((map: MapRead) => void) | undefined
}

/**
 * Multi-select + bulk delete/edit for the map list. Selection is reset
 * when switching to cards view (the checkboxes only render in the table). Bulk
 * delete keeps the still-selected set on partial failure so the operator can
 * retry; bulk edit collapses to the single-map settings modal when exactly one
 * editable map is selected. Maps the user may not edit are filtered out of edits.
 */
export function useMapBulkActions(options: MapBulkActionsOptions) {
  const { filteredMaps, viewMode, openSettings } = options
  const mapsStore = useMaps()
  const toast = useToast()
  const { _t } = usei18n()

  const selectedMaps = ref<Set<string>>(new Set())
  const confirmBulkDelete = ref(false)
  const bulkBusy = ref(false)
  const showBulkEdit = ref(false)

  watch(viewMode, (mode) => {
    if (mode === 'cards' && selectedMaps.value.size > 0) {
      selectedMaps.value = new Set()
    }
  })

  function clearSelection() {
    selectedMaps.value = new Set()
  }

  function toggleMapSelection(name: string) {
    const next = new Set(selectedMaps.value)
    if (next.has(name)) {
      next.delete(name)
    } else {
      next.add(name)
    }
    selectedMaps.value = next
  }

  const selectedCount = computed(() => selectedMaps.value.size)

  const allFilteredSelected = computed(() => {
    const list = filteredMaps()
    if (list.length === 0) {
      return false
    }
    return list.every((b) => selectedMaps.value.has(b.name))
  })

  function toggleSelectAllFiltered(checked: boolean) {
    const next = new Set(selectedMaps.value)
    if (checked) {
      for (const b of filteredMaps()) {
        next.add(b.name)
      }
    } else {
      for (const b of filteredMaps()) {
        next.delete(b.name)
      }
    }
    selectedMaps.value = next
  }

  const selectedNames = computed(() => Array.from(selectedMaps.value))

  const selectedAliases = computed(() => {
    const byName = new Map(mapsStore.maps.value.map((b) => [b.name, b.alias || b.name]))
    return selectedNames.value.map((n) => byName.get(n) ?? n)
  })

  function openBulkDelete() {
    if (selectedCount.value === 0) {
      return
    }
    confirmBulkDelete.value = true
  }

  async function doBulkDelete() {
    if (bulkBusy.value) {
      return
    }
    bulkBusy.value = true
    try {
      const result = await mapsStore.bulkDeleteMaps(selectedNames.value)
      const okCount = result.deleted.length
      const failed = result.failed
      const okSet = new Set(result.deleted)
      const remaining = new Set<string>()
      for (const n of selectedMaps.value) {
        if (!okSet.has(n)) {
          remaining.add(n)
        }
      }
      // Keeps whatever could not be deleted selected, so a retry is one click.
      selectedMaps.value = remaining
      confirmBulkDelete.value = false
      if (failed.length === 0) {
        toast.success(_t('%{n} maps deleted', { n: okCount }))
      } else {
        toast.error(_t('%{ok} deleted, %{fail} failed', { ok: okCount, fail: failed.length }))
      }
    } catch (e: unknown) {
      toast.error(errorText(e, _t('Bulk delete failed')))
      confirmBulkDelete.value = false
    } finally {
      bulkBusy.value = false
    }
  }

  const editableSelectedNames = computed(() => {
    const writable = new Set(mapsStore.maps.value.filter((b) => b.can_edit).map((b) => b.name))
    return selectedNames.value.filter((n) => writable.has(n))
  })

  const editableSelectedAliases = computed(() => {
    const byName = new Map(mapsStore.maps.value.map((b) => [b.name, b.alias || b.name]))
    return editableSelectedNames.value.map((n) => byName.get(n) ?? n)
  })

  function openBulkEdit() {
    if (editableSelectedNames.value.length === 0) {
      toast.error(_t('None of the selected maps is editable (all are read-only).'))
      return
    }
    // A selection of one is a single-map edit, so it opens that map's own
    // settings where the caller offers them.
    if (openSettings && editableSelectedNames.value.length === 1) {
      const map = mapsStore.maps.value.find((b) => b.name === editableSelectedNames.value[0])
      if (map) {
        openSettings(map)
        return
      }
    }
    showBulkEdit.value = true
  }

  /** ``values`` are the ticked fields of the metadata form, as they are stored. */
  async function doBulkEdit(values: Record<string, unknown>) {
    if (bulkBusy.value) {
      return
    }
    // Read into the shape a map is written in: the form describes the click
    // action, the rotation interval and the templates differently from the map
    // itself, and only the ticked fields are touched at all.
    const updates = metadataUpdatesFrom(values)
    if (Object.keys(updates).length === 0) {
      showBulkEdit.value = false
      return
    }
    const targets = editableSelectedNames.value
    if (targets.length === 0) {
      showBulkEdit.value = false
      return
    }
    bulkBusy.value = true
    try {
      const result = await mapsStore.bulkEditMaps(targets, updates)
      showBulkEdit.value = false
      if (result.failed.length === 0) {
        toast.success(_t('Updated %{n} maps', { n: result.updated.length }))
      } else {
        toast.error(
          _t('Updated %{ok}, %{fail} failed', {
            ok: result.updated.length,
            fail: result.failed.length
          })
        )
      }
    } catch (e: unknown) {
      toast.error(errorText(e, _t('Bulk edit failed')))
    } finally {
      bulkBusy.value = false
    }
  }

  return {
    selectedMaps,
    confirmBulkDelete,
    bulkBusy,
    showBulkEdit,
    clearSelection,
    toggleMapSelection,
    selectedCount,
    allFilteredSelected,
    toggleSelectAllFiltered,
    selectedAliases,
    openBulkDelete,
    doBulkDelete,
    editableSelectedNames,
    editableSelectedAliases,
    openBulkEdit,
    doBulkEdit
  }
}
