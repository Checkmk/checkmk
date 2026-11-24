/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import type { MaybeRestApiError } from 'cmk-ui-library/lib/types'
import {
  type Ref,
  type ShallowRef,
  onScopeDispose,
  readonly,
  ref,
  shallowReadonly,
  shallowRef,
  watch
} from 'vue'

import type { ComputedWidgetResponse } from '@/dashboard/types/widget'

export type WidgetDataState<T> =
  | { kind: 'loading' }
  | { kind: 'data'; value: T }
  | { kind: 'no-data'; detail: string }
  | { kind: 'error'; detail: string }

export interface WidgetData<T> {
  state: Readonly<ShallowRef<WidgetDataState<T>>>
  /** Whether a fetch is under way, including a background refresh that keeps the data shown. */
  fetching: Readonly<Ref<boolean>>
  /** When the last fetch succeeded, in milliseconds since the epoch. */
  lastSuccessAt: Readonly<Ref<number | undefined>>
  retry: () => void
  /**
   * Fetch again in the background after `delayMs`, keeping what is shown until the new data is
   * there.
   */
  refresh: (delayMs?: number) => void
}

/** The fetch lifecycle of a widget: refetch on input changes and refresh ticks. */
export function useWidgetData<T>(
  fetch: () => Promise<ComputedWidgetResponse<T>>,
  input: () => unknown,
  tick: () => number
): WidgetData<T> {
  const state = shallowRef<WidgetDataState<T>>({ kind: 'loading' })
  const fetching = ref(false)
  const lastSuccessAt = ref<number | undefined>(undefined)
  let generation = 0
  let refreshPending = false
  let disposed = false
  let delayedRefresh: ReturnType<typeof setTimeout> | undefined

  function start(): void {
    const current = ++generation
    fetching.value = true
    refreshPending = false
    fetch()
      .then(
        (response) => {
          if (current === generation) {
            state.value = { kind: 'data', value: response.value }
            lastSuccessAt.value = Date.now()
          }
        },
        (error: unknown) => {
          if (current === generation) {
            state.value = failureState(error)
          }
        }
      )
      .finally(() => {
        if (current !== generation) {
          return
        }
        fetching.value = false
        if (refreshPending) {
          start()
        }
      })
  }

  function discardInFlight(): void {
    generation += 1
  }

  function refreshNow(): void {
    if (disposed) {
      return
    }
    if (fetching.value) {
      refreshPending = true
      return
    }
    start()
  }

  watch([() => JSON.stringify(input()), tick], ([newInput, newTick], [oldInput, oldTick]) => {
    if (newTick > oldTick) {
      refreshNow()
    } else if (newInput !== oldInput) {
      start()
    }
  })

  function refreshAfter(delayMs = 0): void {
    clearTimeout(delayedRefresh)
    delayedRefresh = setTimeout(refreshNow, delayMs)
  }

  onScopeDispose(() => {
    disposed = true
    clearTimeout(delayedRefresh)
    discardInFlight()
  })

  start()

  return {
    state: shallowReadonly(state),
    fetching: readonly(fetching),
    lastSuccessAt: readonly(lastSuccessAt),
    retry: () => {
      state.value = { kind: 'loading' }
      start()
    },
    refresh: refreshAfter
  }
}

function failureState(error: unknown): { kind: 'no-data' | 'error'; detail: string } {
  if (!(error instanceof CmkApiError)) {
    return { kind: 'error', detail: error instanceof Error ? error.message : String(error) }
  }
  const problem = problemOf(error.body)
  if (error.statusCode === 404) {
    return { kind: 'no-data', detail: problem.title ?? error.message }
  }
  return { kind: 'error', detail: problem.detail ?? problem.title ?? error.message }
}

function problemOf(body: unknown): MaybeRestApiError {
  if (typeof body !== 'object' || body === null) {
    return {}
  }
  const { detail, title } = body as Record<string, unknown>
  return {
    ...(typeof detail === 'string' && { detail }),
    ...(typeof title === 'string' && { title })
  }
}
