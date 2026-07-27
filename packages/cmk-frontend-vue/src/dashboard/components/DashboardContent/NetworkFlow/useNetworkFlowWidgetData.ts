/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, computed, onBeforeMount, ref, watch } from 'vue'

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
 * Fetches on mount and refetches whenever the widget's data parameters (its
 * content configuration and the effective filter context) change.
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
      // of flashing its stale data back on every attempt.
      error.value = null
    } catch (e) {
      if (thisGeneration !== generation) {
        return
      }
      error.value =
        e instanceof CmkApiError
          ? { variant: 'warning', message: e.message }
          : { variant: 'error', message: _t('Failed to load the widget data') }
    }
  }

  onBeforeMount(() => void fetchData())

  const serializedDataParameters = computed(() => JSON.stringify(dataParameters()))
  watch(serializedDataParameters, () => void fetchData())

  return { data, error }
}
