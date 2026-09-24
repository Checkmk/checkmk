/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import type { MaybeRestApiError } from 'cmk-ui-library/lib/types'
import { type ShallowRef, onScopeDispose, shallowReadonly, shallowRef, watch } from 'vue'

import type { ComputedWidgetResponse } from '@/dashboard/types/widget'

export type WidgetDataState<T> =
  | { kind: 'loading' }
  | { kind: 'data'; value: T }
  | { kind: 'no-data'; detail: string }
  | { kind: 'error'; detail: string }

export interface WidgetData<T> {
  state: Readonly<ShallowRef<WidgetDataState<T>>>
  retry: () => void
}

/** The fetch lifecycle of a widget: refetch on input changes and refresh ticks. */
export function useWidgetData<T>(
  fetch: () => Promise<ComputedWidgetResponse<T>>,
  input: () => unknown,
  tick: () => number
): WidgetData<T> {
  const state = shallowRef<WidgetDataState<T>>({ kind: 'loading' })
  let generation = 0
  let inFlight = false
  let refreshPending = false

  function start(): void {
    const current = ++generation
    inFlight = true
    refreshPending = false
    fetch()
      .then(
        (response) => {
          if (current === generation) {
            state.value = { kind: 'data', value: response.value }
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
        inFlight = false
        if (refreshPending) {
          start()
        }
      })
  }

  function discardInFlight(): void {
    generation += 1
  }

  function refresh(): void {
    if (inFlight) {
      refreshPending = true
      return
    }
    start()
  }

  watch([() => JSON.stringify(input()), tick], ([newInput, newTick], [oldInput, oldTick]) => {
    if (newTick > oldTick) {
      refresh()
    } else if (newInput !== oldInput) {
      start()
    }
  })

  onScopeDispose(discardInFlight)

  start()

  return {
    state: shallowReadonly(state),
    retry: () => {
      state.value = { kind: 'loading' }
      start()
    }
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
