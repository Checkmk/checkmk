/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import { type Ref, computed, ref, watch } from 'vue'

import { useMaps, useMapsApis } from '@/maps/services/context'
import { type SuggestionList, namedSuggestions, titledSuggestions } from '@/maps/shared/suggestions'
import type { ObjectType } from '@/maps/types/api'

/** A list while it is still being filled. */
interface MutableSuggestionList {
  items: Ref<Suggestion[]>
  loading: Ref<boolean>
}

export interface ObjectSuggestions {
  hosts: SuggestionList
  services: SuggestionList
  groups: SuggestionList
  aggregations: SuggestionList
  maps: SuggestionList
  /** The picked aggregation's top-level function, when Checkmk surfaced one. */
  aggregationFunctionOf: (aggregationId: string) => string | null
}

interface ObjectSuggestionsOptions {
  connectionId: () => string
  objectType: () => ObjectType | ''
  hostName: () => string
  /**
   * The map a map-link object already points at. The list drops the map being
   * edited -- linking to itself goes nowhere -- but not when that is the link
   * already stored, which would leave the field reading as empty over a
   * binding that is set.
   */
  mapName?: () => string
}

/** Which lists a given object type can be bound to. */
function wantsHosts(type: ObjectType | ''): boolean {
  return type === 'host' || type === 'service' || type === 'line' || type === 'graph'
}

function wantsServices(type: ObjectType | ''): boolean {
  return type === 'service' || type === 'line' || type === 'graph'
}

function groupTypeOf(type: ObjectType | ''): 'hostgroup' | 'servicegroup' | null {
  return type === 'hostgroup' || type === 'servicegroup' ? type : null
}

function emptyList(): MutableSuggestionList {
  return { items: ref([]), loading: ref(false) }
}

/**
 * The monitoring objects an operator can bind a map object to, as dropdown
 * suggestions: hosts, that host's services, host/service groups, BI
 * aggregations and the site's other maps.
 *
 * One list per kind, loaded when the picked object type actually needs it and
 * reloaded when the connection or the host changes. A failed load leaves the
 * list empty and says why in the console, so an empty dropdown is diagnosable
 * instead of looking like "nothing configured".
 *
 * Both editors ask for the same lists — the add-object panel for the draft
 * being placed, the properties card for the object already on the map — so
 * they ask here rather than each fetching for itself.
 */
export function useObjectSuggestions(options: ObjectSuggestionsOptions): ObjectSuggestions {
  const { connectionId, objectType, hostName } = options
  const { objects } = useMapsApis()
  const mapsStore = useMaps()

  const hosts = emptyList()
  const services = emptyList()
  const groups = emptyList()
  const aggregations = emptyList()
  const aggregationFunctions = ref<Record<string, string>>({})

  function warn(what: string): (error: unknown) => never[] {
    return (error) => {
      console.warn(`[Maps] Failed to load ${what}:`, error)
      return []
    }
  }

  async function loadHosts(): Promise<void> {
    hosts.loading.value = true
    hosts.items.value = namedSuggestions(await objects.fetchObjects('host').catch(warn('hosts')))
    hosts.loading.value = false
  }

  // A slower answer for the previously typed host must not overwrite the list
  // of the one now picked, so only the newest request may write.
  let servicesRequest = 0
  async function loadServices(host: string): Promise<void> {
    const request = ++servicesRequest
    services.loading.value = true
    const names = await objects.fetchObjects('service', host).catch(warn('services'))
    if (request === servicesRequest) {
      services.items.value = namedSuggestions(names)
      services.loading.value = false
    }
  }

  /**
   * Drop the services along with the host they belong to. Retiring the request
   * counter is the point: a lookup still out for the host just cleared would
   * otherwise pass the guard above and refill the list under an empty field.
   */
  function clearServices(): void {
    servicesRequest++
    services.items.value = []
    services.loading.value = false
  }

  async function loadGroups(type: 'hostgroup' | 'servicegroup'): Promise<void> {
    groups.loading.value = true
    groups.items.value = namedSuggestions(await objects.fetchObjects(type).catch(warn('groups')))
    groups.loading.value = false
  }

  async function loadAggregations(): Promise<void> {
    aggregations.loading.value = true
    const found = await objects.fetchAggregations().catch(warn('BI aggregations'))
    aggregations.items.value = titledSuggestions(
      found.map((aggregation) => ({ id: aggregation.id, title: aggregation.title }))
    )
    aggregationFunctions.value = Object.fromEntries(
      found.filter((aggregation) => aggregation.function).map((a) => [a.id, a.function as string])
    )
    aggregations.loading.value = false
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
      if (wantsHosts(type)) {
        void loadHosts()
        if (wantsServices(type) && hostName()) {
          void loadServices(hostName())
        }
        return
      }
      const groupType = groupTypeOf(type)
      if (groupType) {
        void loadGroups(groupType)
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

  watch(hostName, (host) => {
    if (!wantsServices(objectType()) || !connectionId()) {
      return
    }
    if (host) {
      void loadServices(host)
    } else {
      clearServices()
    }
  })

  return {
    hosts,
    services,
    groups,
    aggregations,
    maps,
    aggregationFunctionOf: (aggregationId) => aggregationFunctions.value[aggregationId] ?? null
  }
}
