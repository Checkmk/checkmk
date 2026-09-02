/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import { useAuth, useSettings } from '@/maps/services/context'
import type { ViewSwitchOption } from '@/maps/shared/components/MapsViewSwitch.vue'
import type { MapListView } from '@/maps/types/api'

/**
 * Cards-vs-table choice for the map list. A per-user override is persisted in
 * localStorage (keyed by user id) and read synchronously at setup so the first
 * render honours it; the global `map_list_view` setting is only the default.
 * Falls back gracefully when localStorage is unavailable (private mode).
 */
export function useMapListViewMode() {
  const auth = useAuth()
  const settingsStore = useSettings()
  const { _t } = usei18n()

  function viewModeStorageKey(): string {
    return `maps_map_list_view_${auth.user.value?.user_id ?? 'anon'}`
  }
  function readStoredViewMode(): MapListView | null {
    const v = localStorage.getItem(viewModeStorageKey())
    return v === 'table' || v === 'cards' ? v : null
  }
  const localViewMode = ref<MapListView | null>(readStoredViewMode())

  const viewMode = computed<MapListView>(
    () =>
      localViewMode.value ??
      (settingsStore.settings.value.map_list_view === 'table' ? 'table' : 'cards')
  )
  const viewModeOptions = computed<ViewSwitchOption<MapListView>[]>(() => [
    { label: _t('Cards'), value: 'cards' },
    { label: _t('Table'), value: 'table' }
  ])

  function setViewMode(next: MapListView) {
    if (viewMode.value === next) {
      return
    }
    localViewMode.value = next
    try {
      localStorage.setItem(viewModeStorageKey(), next)
    } catch {
      // localStorage unavailable (e.g. private mode); the in-memory ref still applies.
    }
  }

  return { viewMode, viewModeOptions, setViewMode }
}
