/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import { computed, ref, watch } from 'vue'

import { useMaps, useMapsApis } from '@/maps/services/context'
import { type SuggestionList, titledSuggestions } from '@/maps/shared/suggestions'
import type { ObjectType } from '@/maps/types/api'

export interface ObjectSuggestions {
  aggregations: SuggestionList
  maps: SuggestionList
  /** The picked aggregation's top-level function, when Checkmk surfaced one. */
  aggregationFunctionOf: (aggregationId: string) => string | null
}

interface ObjectSuggestionsOptions {
  connectionId: () => string
  objectType: () => ObjectType | ''
  /**
   * The map a map-link object already points at. The list drops the map being
   * edited -- linking to itself goes nowhere -- but not when that is the link
   * already stored, which would leave the field reading as empty over a
   * binding that is set.
   */
  mapName?: () => string
}

/**
 * The BI aggregations and other maps an operator can bind a map object to, as
 * dropdown suggestions. Hosts, services and groups are not listed here: their
 * fields search Checkmk's own autocompleters as the operator types.
 *
 * Each list is loaded when the picked object type actually needs it and
 * reloaded when the connection changes. A failed load leaves the list empty
 * and says why in the console, so an empty dropdown is diagnosable instead of
 * looking like "nothing configured".
 *
 * Both editors ask for the same lists — the add-object panel for the draft
 * being placed, the properties card for the object already on the map — so
 * they ask here rather than each fetching for itself.
 */
export function useObjectSuggestions(options: ObjectSuggestionsOptions): ObjectSuggestions {
  const { connectionId, objectType } = options
  const { objects } = useMapsApis()
  const mapsStore = useMaps()

  const aggregationItems = ref<Suggestion[]>([])
  const loadingAggregations = ref(false)
  const aggregationFunctions = ref<Record<string, string>>({})

  async function loadAggregations(): Promise<void> {
    loadingAggregations.value = true
    const found = await objects.fetchAggregations().catch((error: unknown) => {
      console.warn('[Maps] Failed to load BI aggregations:', error)
      return []
    })
    aggregationItems.value = titledSuggestions(
      found.map((aggregation) => ({ id: aggregation.id, title: aggregation.title }))
    )
    aggregationFunctions.value = Object.fromEntries(
      found.filter((aggregation) => aggregation.function).map((a) => [a.id, a.function as string])
    )
    loadingAggregations.value = false
  }

  const maps: SuggestionList = {
    items: computed(() => {
      const self = mapsStore.currentMap.value?.name
      const bound = options.mapName?.()
      return titledSuggestions(
        mapsStore.maps.value
          .filter((map) => map.name !== self || map.name === bound)
          .map((map) => ({ id: map.name, title: map.alias }))
      )
    }),
    loading: mapsStore.loading
  }

  watch(
    () => [objectType(), connectionId()] as const,
    ([type, connection]) => {
      if (!connection) {
        return
      }
      if (type === 'aggregation') {
        void loadAggregations()
        return
      }
      if (type === 'map' && mapsStore.maps.value.length === 0) {
        void mapsStore.fetchMaps()
      }
    },
    { immediate: true }
  )

  return {
    aggregations: { items: aggregationItems, loading: loadingAggregations },
    maps,
    aggregationFunctionOf: (aggregationId) => aggregationFunctions.value[aggregationId] ?? null
  }
}
