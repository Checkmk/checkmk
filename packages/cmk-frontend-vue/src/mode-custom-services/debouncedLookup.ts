/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onScopeDispose, ref, watch } from 'vue'

export type Lookup<Result> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; result: Result }
  | { status: 'failed'; error: unknown; timedOut: boolean }

export interface LookupOptions {
  debounceMs: number
  timeoutMs: number
}

function withSortedKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(withSortedKeys)
  }
  if (typeof value === 'object' && value !== null) {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
        .map(([key, entry]) => [key, withSortedKeys(entry)])
    )
  }
  return value
}

/**
 * Looks up the request ``getRequest`` returns, and again whenever it changes. Changes are
 * debounced, a superseded lookup is aborted and its answer dropped, and a lookup that takes longer
 * than ``timeoutMs`` fails. A null request looks nothing up.
 */
export function useDebouncedLookup<Request, Result>(
  getRequest: () => Request | null,
  lookup: (request: Request, signal: AbortSignal) => Promise<Result>,
  { debounceMs, timeoutMs }: LookupOptions
): Readonly<Ref<Lookup<Result>>> {
  const state = ref<Lookup<Result>>({ status: 'idle' }) as Ref<Lookup<Result>>
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let inFlight: AbortController | null = null

  function cancel(): void {
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    inFlight?.abort()
    inFlight = null
  }

  async function load(request: Request): Promise<void> {
    const controller = new AbortController()
    inFlight = controller
    let timedOut = false
    const timeout = setTimeout(() => {
      timedOut = true
      controller.abort()
    }, timeoutMs)
    try {
      const result = await lookup(request, controller.signal)
      if (inFlight === controller) {
        state.value = { status: 'done', result }
      }
    } catch (error) {
      if (inFlight === controller) {
        state.value = { status: 'failed', error, timedOut }
      }
    } finally {
      clearTimeout(timeout)
      if (inFlight === controller) {
        inFlight = null
      }
    }
  }

  function schedule(): void {
    cancel()
    const request = getRequest()
    if (request === null) {
      state.value = { status: 'idle' }
      return
    }
    // Shown at once, so no result of an earlier request is left standing during the debounce
    state.value = { status: 'loading' }
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      void load(request)
    }, debounceMs)
  }

  // A serialized key with sorted keys, so an equal request in a new object or another key order
  // does not ask again
  watch(() => JSON.stringify(withSortedKeys(getRequest())), schedule, { immediate: true })
  onScopeDispose(cancel)

  return state
}
