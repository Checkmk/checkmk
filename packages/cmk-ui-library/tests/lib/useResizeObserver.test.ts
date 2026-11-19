/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { FakeResizeObserver, useFakeResizeObserver } from 'cmk-ui-library/vitest.resize-observer'
import { describe, expect, test, vi } from 'vitest'
import { type Ref, effectScope, nextTick, ref } from 'vue'

// `onScopeDispose` needs an active effect scope; run the composable inside one we can stop on demand.
function inScope<T>(fn: () => T): { api: T; stop: () => void } {
  const scope = effectScope()
  const api = scope.run(fn)!
  return { api, stop: () => scope.stop() }
}

describe('useResizeObserver', () => {
  useFakeResizeObserver(FakeResizeObserver)

  test('observes the element once the ref is populated', async () => {
    const target: Ref<Element | null> = ref(null)
    const { api } = inScope(() => useResizeObserver(() => {}))
    api.observe(target)

    const el = document.createElement('div')
    target.value = el
    await nextTick()

    expect([...FakeResizeObserver.instances[0]!.observed]).toEqual([el])
  })

  test('re-observes when the element changes, dropping the previous one', async () => {
    const target: Ref<Element | null> = ref(null)
    const { api } = inScope(() => useResizeObserver(() => {}))
    api.observe(target)

    const first = document.createElement('div')
    const second = document.createElement('div')
    target.value = first
    await nextTick()
    target.value = second
    await nextTick()

    expect([...FakeResizeObserver.instances[0]!.observed]).toEqual([second])
  })

  test('stops observing when the ref becomes null', async () => {
    const target: Ref<Element | null> = ref<Element | null>(document.createElement('div'))
    const { api } = inScope(() => useResizeObserver(() => {}))
    api.observe(target)
    await nextTick()
    target.value = null
    await nextTick()

    expect(FakeResizeObserver.instances[0]!.observed.size).toBe(0)
  })

  test('forwards resize entries to the callback', () => {
    const onResize = vi.fn()
    inScope(() => useResizeObserver(onResize))

    const entries = [{ contentRect: { width: 10 } }] as unknown as ResizeObserverEntry[]
    FakeResizeObserver.instances[0]!.fire(entries)

    expect(onResize).toHaveBeenCalledWith(entries, expect.anything())
  })

  test('disconnects when the owning scope is disposed', async () => {
    const target: Ref<Element | null> = ref<Element | null>(document.createElement('div'))
    const { api, stop } = inScope(() => useResizeObserver(() => {}))
    api.observe(target)
    await nextTick()
    const disconnect = vi.spyOn(FakeResizeObserver.instances[0]!, 'disconnect')

    stop()

    expect(disconnect).toHaveBeenCalled()
  })

  test('is a no-op when ResizeObserver is unavailable', async () => {
    vi.stubGlobal('ResizeObserver', undefined)
    const target: Ref<Element | null> = ref(null)
    const { api, stop } = inScope(() => useResizeObserver(() => {}))

    expect(() => api.observe(target)).not.toThrow()
    target.value = document.createElement('div')
    await nextTick()
    expect(() => {
      stop()
    }).not.toThrow()
    expect(FakeResizeObserver.instances).toHaveLength(0)
  })
})
