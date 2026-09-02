/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref, watch } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import type { MapElement, ObjectDetails } from '@/maps/types/api'

interface ObjectDetailsFetchOptions {
  object: () => MapElement | null
  connectionId: () => string | null | undefined
}

/**
 * On-demand fetch of an object's rich details (long_output, comments,
 * downtimes, topology), kept off the streamed ObjectState because they're
 * large and rarely change. Refetched whenever the selected
 * host/service/connection changes. The CMK perfometer is not fetched here —
 * it comes from the GUI (usePerfometer) on the streamed perf_data.
 */
export function useObjectDetailsFetch(options: ObjectDetailsFetchOptions) {
  const { object, connectionId } = options
  const { connections: connectionsApi } = useMapsApis()

  const details = ref<ObjectDetails | null>(null)

  // Source the watch on primitive keys (not the reactive object) so it fires
  // only when selection actually changes — state-stream updates that re-create
  // the prop reference would otherwise cause refetches on every tick.
  watch(
    [
      () => object()?.type,
      () => object()?.host_name,
      () => object()?.service_description,
      connectionId
    ],
    async ([objType, host, service, connId]) => {
      details.value = null
      if (!connId || !host) {
        return
      }
      if (objType !== 'host' && objType !== 'service') {
        return
      }
      if (objType === 'service' && !service) {
        return
      }
      const reqService = objType === 'service' ? (service ?? null) : null
      try {
        const detailsRes = await connectionsApi.fetchObjectDetails(
          connId,
          objType,
          host,
          reqService
        )
        // Stale-response guard: between the await and now the user may have
        // clicked another object. Match all three identity fields so a host
        // response doesn't land on a same-named service or vice versa.
        // Note: service_description may be undefined on host MapElements
        // (Flow Map synthesises hosts without it) — normalise to null
        // before comparing so the guard doesn't reject legitimate hosts.
        const currentService = object()?.service_description ?? null
        if (
          object()?.type === objType &&
          object()?.host_name === host &&
          currentService === reqService
        ) {
          details.value = detailsRes ?? null
        }
      } catch {
        details.value = null
      }
    },
    { immediate: true }
  )

  return { details }
}
