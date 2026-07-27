/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n from 'cmk-ui-library/lib/i18n'
import useTimer from 'cmk-ui-library/lib/useTimer'
import { type Ref, computed, onBeforeMount, onBeforeUnmount, onMounted, ref, watch } from 'vue'

/**
 * How often the widgets reload their data. The dashboard has no configurable
 * refresh interval, so this matches what the graph and figure widgets use.
 */
export const NETWORK_FLOW_REFRESH_INTERVAL_MS = 60_000

/**
 * A backend-reported condition (flow monitoring disabled, database unreachable,
 * query failed) is an expected state shown as a warning; anything unexpected is
 * an error - mirroring how the ntop widget distinguishes severity.
 */
export interface NetworkFlowWidgetError {
  variant: 'warning' | 'error'
  message: string
}

export interface NetworkFlowWidgetData<TData> {
  data: Ref<TData | undefined>
  error: Ref<NetworkFlowWidgetError | null>
}

/**
 * Data fetching shared by the network flow widgets.
 *
 * Fetches on mount, reloads every NETWORK_FLOW_REFRESH_INTERVAL_MS, and
 * refetches whenever the widget's data parameters (its content configuration
 * and the effective filter context) change.
 *
 * @param fetchResponse - performs the request; called with no arguments so the
 * caller can close over its reactive props
 * @param transform - maps a response to the shape the widget renders
 * @param dataParameters - everything the response depends on; a change refetches
 */
export function useNetworkFlowWidgetData<TResponse, TData>(
  fetchResponse: () => Promise<TResponse>,
  transform: (response: TResponse) => TData,
  dataParameters: () => unknown
): NetworkFlowWidgetData<TData> {
  const { _t } = usei18n()

  const data = ref<TData | undefined>(undefined) as Ref<TData | undefined>
  const error = ref<NetworkFlowWidgetError | null>(null)

  // Requests can overlap - a refetch may start while an earlier one is still in
  // flight - and they are not guaranteed to resolve in order. Only the newest
  // request may write the state, so a slow earlier response cannot overwrite a
  // newer one.
  let generation = 0

  const fetchData = async (): Promise<void> => {
    const thisGeneration = ++generation
    try {
      // data is deliberately not reset here: a refetch keeps rendering the
      // previous result until the new one arrives, so the widget does not
      // flicker back into its loading state.
      const transformed = transform(await fetchResponse())
      if (thisGeneration !== generation) {
        return
      }
      data.value = transformed
      // The error is cleared here rather than before the request, so a widget
      // in an error state stays in it until a request actually succeeds instead
      // of flashing its stale data back on every attempt. An error state
      // therefore recovers on its own with the next successful reload.
      error.value = null
      timer.reportSuccess()
    } catch (e) {
      if (thisGeneration !== generation) {
        return
      }
      error.value =
        e instanceof CmkApiError
          ? { variant: 'warning', message: e.message }
          : { variant: 'error', message: _t('Failed to load the widget data') }
      // Back off instead of hammering a flow database that keeps refusing.
      timer.reportFailure()
    }
  }

  // A hidden tab does not need current data, and the queries are not cheap.
  // Coming back into view fetches once so the widget is up to date right away
  // rather than after the rest of the interval.
  const reload = (): void => {
    if (document.hidden) {
      return
    }
    void fetchData()
  }

  const timer = useTimer(reload, NETWORK_FLOW_REFRESH_INTERVAL_MS)

  onBeforeMount(() => void fetchData())

  const serializedDataParameters = computed(() => JSON.stringify(dataParameters()))
  watch(serializedDataParameters, () => void fetchData())

  onMounted(() => {
    timer.start()
    document.addEventListener('visibilitychange', reload)
  })

  onBeforeUnmount(() => {
    // Invalidate in-flight requests before stopping the timer: reporting their
    // outcome afterwards would restart it and leak the interval.
    generation++
    timer.stop()
    document.removeEventListener('visibilitychange', reload)
  })

  return { data, error }
}
