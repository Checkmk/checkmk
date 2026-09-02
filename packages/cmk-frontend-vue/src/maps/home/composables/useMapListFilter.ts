/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { useAuth, useMaps } from '@/maps/services/context'
import type { MapRead } from '@/maps/types/api'
import { type MapOwnerKind, mapOwnerKind } from '@/maps/utils/mapVisibility'

/** "All" plus whichever owner kinds are actually present in the list. */
export type MapScope = MapOwnerKind | 'all'

export interface ScopeOption {
  value: MapScope
  label: TranslatedString
}

/**
 * Provenance is shown per card and per row (owner + visibility), so the list is
 * one flat set ordered yours → others → built-in instead of stacked owner
 * sections. This is the ordering, the search and the scope filter that narrows
 * it.
 */
const OWNER_ORDER: readonly MapOwnerKind[] = ['you', 'other', 'builtin']

export function useMapListFilter(): {
  searchQuery: Ref<string>
  /**
   * The active scope. Reading it never returns a scope whose group is gone (the
   * last map of that kind deleted) — it falls back to "all" rather than showing
   * an empty list behind a stale filter.
   */
  scope: Ref<MapScope>
  scopeOptions: ComputedRef<ScopeOption[]>
  showScopeFilter: ComputedRef<boolean>
  displayedMaps: ComputedRef<MapRead[]>
  /** True while the displayed order matches the store's, so a drag may reorder. */
  isOrderPristine: ComputedRef<boolean>
} {
  const { _t } = usei18n()
  const auth = useAuth()
  const maps = useMaps()

  const searchQuery = ref('')
  const chosenScope = ref<MapScope>('all')

  // A map hidden from lists stays visible to an administrator, who is the one
  // who can unhide it.
  const visibleMaps = computed(() =>
    auth.isAdmin.value
      ? maps.maps.value
      : maps.maps.value.filter((map) => map.show_in_lists !== false)
  )

  /**
   * The list in its display order, each map with the owner kind the filter and
   * the ordering both need. Ordering does not depend on the query, so it is
   * done once here instead of on every keystroke; bucketing keeps each block in
   * the store's own sort order.
   */
  const orderedMaps = computed<{ map: MapRead; kind: MapOwnerKind }[]>(() => {
    const userId = auth.user.value?.user_id
    const buckets = new Map<MapOwnerKind, { map: MapRead; kind: MapOwnerKind }[]>(
      OWNER_ORDER.map((kind) => [kind, []])
    )
    for (const map of visibleMaps.value) {
      const kind = mapOwnerKind(map, userId)
      buckets.get(kind)?.push({ map, kind })
    }
    return OWNER_ORDER.flatMap((kind) => buckets.get(kind) ?? [])
  })

  const presentKinds = computed<Set<MapOwnerKind>>(
    () => new Set(orderedMaps.value.map((entry) => entry.kind))
  )

  /** Only worth a filter once more than one owner kind is present. */
  const showScopeFilter = computed(() => presentKinds.value.size > 1)

  const scopeOptions = computed<ScopeOption[]>(() => {
    const owned: ScopeOption[] = [
      { value: 'you', label: _t('Yours') },
      { value: 'other', label: _t('Others') },
      { value: 'builtin', label: _t('Built-in') }
    ]
    return [
      { value: 'all', label: _t('All') },
      ...owned.filter((option) => presentKinds.value.has(option.value as MapOwnerKind))
    ]
  })

  const scope = computed<MapScope>({
    get: () =>
      scopeOptions.value.some((option) => option.value === chosenScope.value)
        ? chosenScope.value
        : 'all',
    set: (value) => {
      chosenScope.value = value
    }
  })

  const displayedMaps = computed<MapRead[]>(() => {
    const query = searchQuery.value.trim().toLowerCase()
    const wanted = scope.value
    return orderedMaps.value
      .filter(
        ({ map, kind }) =>
          (wanted === 'all' || kind === wanted) &&
          (!query ||
            map.name.toLowerCase().includes(query) ||
            map.alias.toLowerCase().includes(query))
      )
      .map(({ map }) => map)
  })

  const isOrderPristine = computed(() => !searchQuery.value.trim() && presentKinds.value.size <= 1)

  return {
    searchQuery,
    scope,
    scopeOptions,
    showScopeFilter,
    displayedMaps,
    isOrderPristine
  }
}
