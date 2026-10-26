/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref, watch } from 'vue'

import { useMapsApis, useStates } from '@/maps/services/context'
import type { MapElement, ObjectDetails } from '@/maps/types/api'

interface ObjectDetailsFetchOptions {
  object: () => MapElement | null
  connectionId: () => string | null | undefined
}

/**
 * On-demand fetch of an object's rich details (long_output, comments,
 * downtimes, topology), kept off the streamed ObjectState because they're
 * large and rarely change. Refetched whenever the selected
 * host/service/connection changes, and after a command, which is what adds a
 * comment or a downtime. The CMK perfometer is not fetched here — it comes from
 * the GUI (usePerfometer) on the streamed perf_data.
 */
export function useObjectDetailsFetch(options: ObjectDetailsFetchOptions) {
  const { object, connectionId } = options
  const { connections: connectionsApi } = useMapsApis()
  const statesStore = useStates()

  const details = ref<ObjectDetails | null>(null)
  let generation = 0

  // A reload after a command keeps what is shown when it fails; a new selection
  // starts empty.
  async function load(keepOnError: boolean): Promise<void> {
    const current = ++generation
    const objType = object()?.type
    const host = object()?.host_name
    const service = object()?.service_description
    const connId = connectionId()
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
      const detailsRes = await connectionsApi.fetchObjectDetails(connId, objType, host, reqService)
      if (current === generation) {
        details.value = detailsRes ?? null
      }
    } catch {
      if (current === generation && !keepOnError) {
        details.value = null
      }
    }
  }

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
    () => {
      details.value = null
      void load(false)
    },
    { immediate: true }
  )
  // Kept on screen while it reloads, so the list does not blink.
  watch(statesStore.commandRefreshes, () => void load(true))

  return { details }
}
