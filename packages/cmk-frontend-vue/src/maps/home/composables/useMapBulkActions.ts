/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import { useMaps, useToast } from '@/maps/services/context'
import { errorText } from '@/maps/shared/errorText'
import type { MapRead } from '@/maps/types/api'

/** Delete is the one bulk action, so only what may be deleted is selectable. */
export function isBulkSelectable(map: MapRead): boolean {
  return map.can_delete === true
}

interface MapBulkActionsOptions {
  filteredMaps: () => MapRead[]
}

/**
 * Multi-select + bulk delete for the map list. Bulk delete keeps the
 * still-selected set on partial failure so the operator can retry.
 */
export function useMapBulkActions(options: MapBulkActionsOptions) {
  const { filteredMaps } = options
  const mapsStore = useMaps()
  const toast = useToast()
  const { _t } = usei18n()

  const selectedMaps = ref<Set<string>>(new Set())
  const confirmBulkDelete = ref(false)
  const bulkBusy = ref(false)

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

  function setSelected(names: string[], checked: boolean) {
    const next = new Set(selectedMaps.value)
    for (const name of names) {
      if (checked) {
        next.add(name)
      } else {
        next.delete(name)
      }
    }
    selectedMaps.value = next
  }

  const selectedCount = computed(() => selectedMaps.value.size)

  const selectableNames = computed(() =>
    filteredMaps()
      .filter(isBulkSelectable)
      .map((map) => map.name)
  )

  const selectableCount = computed(() => selectableNames.value.length)

  const allFilteredSelected = computed(() => {
    const names = selectableNames.value
    return names.length > 0 && names.every((name) => selectedMaps.value.has(name))
  })

  function toggleSelectAllFiltered(checked: boolean) {
    setSelected(selectableNames.value, checked)
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

  return {
    selectedMaps,
    confirmBulkDelete,
    bulkBusy,
    clearSelection,
    toggleMapSelection,
    setSelected,
    selectedCount,
    selectableCount,
    allFilteredSelected,
    toggleSelectAllFiltered,
    selectedAliases,
    openBulkDelete,
    doBulkDelete
  }
}
