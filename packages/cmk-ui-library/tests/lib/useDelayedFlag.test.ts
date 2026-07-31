/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { LOADING_AFFORDANCE_DELAY_MS, useDelayedFlag } from 'cmk-ui-library/lib/useDelayedFlag'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { type Ref, effectScope, nextTick, ref } from 'vue'

const DELAY = 1000

// `onScopeDispose` needs an active effect scope; run the composable inside one we can stop on demand.
function inScope<T>(fn: () => T): { api: T; stop: () => void } {
  const scope = effectScope()
  const api = scope.run(fn)!
  return { api, stop: () => scope.stop() }
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

test('the shared loading threshold is one second', () => {
  expect(LOADING_AFFORDANCE_DELAY_MS).toBe(1000)
})

describe('useDelayedFlag', () => {
  test('stays false until the source has been true for the whole delay', async () => {
    const source: Ref<boolean> = ref(true)
    const { api: flag } = inScope(() => useDelayedFlag(() => source.value, DELAY))

    expect(flag.value).toBe(false)

    vi.advanceTimersByTime(DELAY - 1)
    expect(flag.value).toBe(false)

    vi.advanceTimersByTime(1)
    expect(flag.value).toBe(true)
  })

  test('never turns true when the source drops before the delay elapses', async () => {
    const source: Ref<boolean> = ref(true)
    const { api: flag } = inScope(() => useDelayedFlag(() => source.value, DELAY))

    vi.advanceTimersByTime(DELAY - 1)
    source.value = false
    await nextTick()

    // Running past the original deadline must not resurrect the flag.
    vi.advanceTimersByTime(DELAY)
    expect(flag.value).toBe(false)
  })

  test('drops back to false immediately once the source goes false', async () => {
    const source: Ref<boolean> = ref(true)
    const { api: flag } = inScope(() => useDelayedFlag(() => source.value, DELAY))

    vi.advanceTimersByTime(DELAY)
    expect(flag.value).toBe(true)

    source.value = false
    await nextTick()
    expect(flag.value).toBe(false)
  })

  test('restarts the full delay when the source becomes true again', async () => {
    const source: Ref<boolean> = ref(true)
    const { api: flag } = inScope(() => useDelayedFlag(() => source.value, DELAY))

    vi.advanceTimersByTime(DELAY - 1)
    source.value = false
    await nextTick()
    source.value = true
    await nextTick()

    // A leftover timer from the first attempt would fire after 1 more ms.
    vi.advanceTimersByTime(DELAY - 1)
    expect(flag.value).toBe(false)

    vi.advanceTimersByTime(1)
    expect(flag.value).toBe(true)
  })

  test('starts false and never fires when the source is false from the outset', () => {
    const source: Ref<boolean> = ref(false)
    const { api: flag } = inScope(() => useDelayedFlag(() => source.value, DELAY))

    expect(flag.value).toBe(false)
    vi.advanceTimersByTime(DELAY * 2)
    expect(flag.value).toBe(false)
  })

  test('cancels the pending delay when the scope is disposed', () => {
    const source: Ref<boolean> = ref(true)
    const { api: flag, stop } = inScope(() => useDelayedFlag(() => source.value, DELAY))

    stop()
    vi.advanceTimersByTime(DELAY)

    expect(flag.value).toBe(false)
    expect(vi.getTimerCount()).toBe(0)
  })
})
