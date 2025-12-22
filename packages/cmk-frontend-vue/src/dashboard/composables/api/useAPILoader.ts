/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, readonly, ref } from 'vue'

import type { CmkFetchResponse } from '@/lib/cmkFetch.ts'

type LoaderOptions<T> = {
  fetcher: () => Promise<CmkFetchResponse>
  initial?: T | null
}

function getErrorMessage(e: unknown): string {
  if (e instanceof Error) {
    return e.message
  }
  if (typeof e === 'string') {
    return e
  }
  try {
    return JSON.stringify(e)
  } catch {
    return String(e)
  }
}

export function useAPILoader<T>({ fetcher, initial = null }: LoaderOptions<T>) {
  const _state = ref<T | null>(initial)
  const _isLoading = ref(false) // true only on first load (when empty)
  const _error = ref<string | null>(null)
  const _lastLoadedAt = ref<number | null>(null)

  let _inFlight: Promise<void> | null = null

  async function _runFetch(params: { firstLoad: boolean }): Promise<void> {
    const { firstLoad } = params

    if (firstLoad) {
      _isLoading.value = true
    }

    _error.value = null

    try {
      const resp = await fetcher()
      _state.value = await resp.json()
      _lastLoadedAt.value = Date.now()
    } catch (e: unknown) {
      _error.value = getErrorMessage(e)
      // keep showing previous data on error
    } finally {
      if (firstLoad) {
        _isLoading.value = false
      }
    }
  }

  async function ensureLoaded(forceRefresh = false): Promise<void> {
    if (!forceRefresh) {
      if (_state.value) {
        if (_inFlight !== null) {
          await _inFlight
        }
        return
      }

      if (_inFlight !== null) {
        await _inFlight
        return
      }

      _inFlight = _runFetch({ firstLoad: true }).finally(() => {
        _inFlight = null
      })

      await _inFlight
      return
    }

    await refresh()
  }

  async function refresh(): Promise<void> {
    if (_inFlight !== null) {
      await _inFlight
      return
    }

    const firstLoad = !_state.value

    _inFlight = _runFetch({ firstLoad }).finally(() => {
      _inFlight = null
    })

    await _inFlight
  }

  function invalidate(): void {
    _state.value = null
  }

  return {
    state: readonly(_state) as Readonly<Ref<T | null>>,
    isLoading: readonly(_isLoading),
    error: readonly(_error),
    lastLoadedAt: readonly(_lastLoadedAt),
    ensureLoaded,
    refresh,
    invalidate
  } as const
}
