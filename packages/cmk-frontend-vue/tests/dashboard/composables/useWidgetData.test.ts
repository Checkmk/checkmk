/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { describe, expect, it } from 'vitest'
import { defineComponent, ref } from 'vue'

import { type WidgetData, useWidgetData } from '@/dashboard/composables/useWidgetData'
import type { ComputedWidgetResponse } from '@/dashboard/types/widget'

import { flushPromises } from '@tests/dashboard/utils'

interface Deferred {
  resolve: (value: string) => void
  reject: (error: unknown) => void
}

function harness() {
  const calls: Deferred[] = []
  const input = ref<Record<string, unknown>>({ host: 'a' })
  const tick = ref(0)
  let state: WidgetData<string>['state'] | undefined
  let retry: (() => void) | undefined

  const { unmount } = render(
    defineComponent({
      setup() {
        const data = useWidgetData(
          () =>
            new Promise<ComputedWidgetResponse<string>>((resolve, reject) => {
              calls.push({
                resolve: (value) => resolve({ domainType: 'widget-compute', value }),
                reject
              })
            }),
          () => input.value,
          () => tick.value
        )
        state = data.state
        retry = data.retry
        return () => null
      }
    })
  )

  return {
    calls,
    input,
    tick,
    state: () => state!.value,
    retry: () => retry!(),
    unmount,
    answer: async (index: number, value: string) => {
      calls[index]!.resolve(value)
      await flushPromises()
    },
    fail: async (index: number, error: unknown) => {
      calls[index]!.reject(error)
      await flushPromises()
    }
  }
}

function apiError(status: number, body: Record<string, string>): CmkApiError {
  return new CmkApiError('Error in fetch response', null, '', status, body)
}

describe('useWidgetData', () => {
  it('fetches once on mount', () => {
    const { calls } = harness()

    expect(calls).toHaveLength(1)
  })

  it('fetches once more when the refresh counter rises', async () => {
    const h = harness()
    await h.answer(0, 'first')

    h.tick.value = 1
    await flushPromises()

    expect(h.calls).toHaveLength(2)
  })

  it('fetches once more when the input changes', async () => {
    const h = harness()
    await h.answer(0, 'first')

    h.input.value = { host: 'b' }
    await flushPromises()

    expect(h.calls).toHaveLength(2)
  })

  it('discards the response to an earlier input', async () => {
    const h = harness()
    h.input.value = { host: 'b' }
    await flushPromises()

    await h.answer(1, 'for b')
    await h.answer(0, 'for a')

    expect(h.state()).toEqual({ kind: 'data', value: 'for b' })
  })

  it('does not fetch while a refresh finds a fetch in flight', async () => {
    const h = harness()

    h.tick.value = 1
    await flushPromises()

    expect(h.calls).toHaveLength(1)
  })

  it('treats a range change with a tick as a refresh', async () => {
    const h = harness()

    h.tick.value = 1
    h.input.value = { host: 'a', range: 'moved' }
    await flushPromises()

    expect(h.calls).toHaveLength(1)
  })

  it('fetches once after the fetch in flight, however many refreshes arrived', async () => {
    const h = harness()
    h.tick.value = 1
    await flushPromises()
    h.tick.value = 2
    await flushPromises()

    await h.answer(0, 'first')

    expect(h.calls).toHaveLength(2)
  })

  it('draws a response that answers after a refresh', async () => {
    const h = harness()
    h.tick.value = 1
    await flushPromises()

    await h.answer(0, 'slow')

    expect(h.state()).toEqual({ kind: 'data', value: 'slow' })
  })

  it('treats a range change without a tick as an input change', async () => {
    const h = harness()

    h.input.value = { host: 'a', range: 'picked' }
    await flushPromises()

    expect(h.calls).toHaveLength(2)
  })

  it('keeps the previous value while a refetch runs', async () => {
    const h = harness()
    await h.answer(0, 'first')

    h.tick.value = 1
    await flushPromises()

    expect(h.state()).toEqual({ kind: 'data', value: 'first' })
  })

  it('maps a 404 to the no-data state', async () => {
    const h = harness()

    await h.fail(0, apiError(404, { title: 'Widget not found', detail: 'Gone' }))

    expect(h.state()).toEqual({ kind: 'no-data', detail: 'Widget not found' })
  })

  it('maps any other failure to the error state', async () => {
    const h = harness()

    await h.fail(0, apiError(503, { title: 'Monitoring data source unavailable', detail: 'down' }))

    expect(h.state()).toEqual({ kind: 'error', detail: 'down' })
  })

  it('fetches once on retry', async () => {
    const h = harness()
    await h.fail(0, apiError(503, { title: 'Unavailable' }))

    h.retry()
    await flushPromises()

    expect(h.calls).toHaveLength(2)
  })

  it('fetches at once on retry while a refresh runs', async () => {
    const h = harness()
    await h.fail(0, apiError(503, { title: 'Unavailable' }))
    h.tick.value = 1
    await flushPromises()

    h.retry()
    await flushPromises()

    expect(h.calls).toHaveLength(3)
  })

  it('returns to the loading state on retry', async () => {
    const h = harness()
    await h.fail(0, apiError(503, { title: 'Unavailable' }))

    h.retry()
    await flushPromises()

    expect(h.state()).toEqual({ kind: 'loading' })
  })

  it('does not fetch when the input is rebuilt with equal values', async () => {
    const h = harness()
    await h.answer(0, 'first')

    h.input.value = { host: 'a' }
    await flushPromises()

    expect(h.calls).toHaveLength(1)
  })

  it('keeps the error state while a refetch runs', async () => {
    const h = harness()
    await h.fail(0, apiError(503, { title: 'Unavailable' }))

    h.tick.value = 1
    await flushPromises()

    expect(h.state()).toEqual({ kind: 'error', detail: 'Unavailable' })
  })

  it('replaces a drawn value with the error state when a refetch fails', async () => {
    const h = harness()
    await h.answer(0, 'first')
    h.tick.value = 1
    await flushPromises()

    await h.fail(1, apiError(503, { title: 'Unavailable' }))

    expect(h.state()).toEqual({ kind: 'error', detail: 'Unavailable' })
  })

  it('does not fetch a pending refresh after unmount', async () => {
    const h = harness()
    h.tick.value = 1
    await flushPromises()

    h.unmount()
    await h.answer(0, 'late')

    expect(h.calls).toHaveLength(1)
  })

  it('ignores a response that answers after unmount', async () => {
    const h = harness()

    h.unmount()
    await h.answer(0, 'late')

    expect(h.state()).toEqual({ kind: 'loading' })
  })
})
