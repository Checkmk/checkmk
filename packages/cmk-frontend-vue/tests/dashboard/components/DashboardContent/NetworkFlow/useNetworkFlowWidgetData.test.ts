/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, defineComponent, h, nextTick, ref } from 'vue'

import {
  NETWORK_FLOW_REFRESH_INTERVAL_MS,
  type NetworkFlowWidgetData,
  useNetworkFlowWidgetData
} from '@/dashboard/components/DashboardContent/NetworkFlow/useNetworkFlowWidgetData'

interface Response {
  count: number
}

/**
 * The composable uses lifecycle hooks, so it needs a mounted component. The
 * returned state is captured so the assertions can read it directly.
 */
function renderHarness(
  fetchResponse: () => Promise<Response>,
  dataParameters: Ref<unknown> = ref('unchanged')
): NetworkFlowWidgetData<string> & { unmount: () => void } {
  let state: NetworkFlowWidgetData<string> | undefined = undefined
  const { unmount } = render(
    defineComponent({
      setup() {
        state = useNetworkFlowWidgetData(
          fetchResponse,
          (response) => `count: ${response.count}`,
          () => dataParameters.value
        )
        return () => h('div')
      }
    })
  )
  return { ...state!, unmount }
}

describe('useNetworkFlowWidgetData', () => {
  it('starts without data and fetches the transformed response on mount', async () => {
    const fetchResponse = vi.fn().mockResolvedValue({ count: 1 })

    const state = renderHarness(fetchResponse)
    expect(state.data.value).toBeUndefined()
    expect(state.error.value).toBeNull()

    await vi.waitFor(() => expect(state.data.value).toBe('count: 1'))
    expect(fetchResponse).toHaveBeenCalledTimes(1)
  })

  it('refetches when the data parameters change', async () => {
    const fetchResponse = vi
      .fn()
      .mockResolvedValueOnce({ count: 1 })
      .mockResolvedValueOnce({ count: 2 })
    const dataParameters = ref<unknown>({ dimension: 'hosts' })

    const state = renderHarness(fetchResponse, dataParameters)
    await vi.waitFor(() => expect(state.data.value).toBe('count: 1'))

    dataParameters.value = { dimension: 'autonomous_systems' }
    await nextTick()

    await vi.waitFor(() => expect(state.data.value).toBe('count: 2'))
    expect(fetchResponse).toHaveBeenCalledTimes(2)
  })

  it('does not refetch when the data parameters are reassigned to an equal value', async () => {
    const fetchResponse = vi.fn().mockResolvedValue({ count: 1 })
    const dataParameters = ref<unknown>({ dimension: 'hosts' })

    const state = renderHarness(fetchResponse, dataParameters)
    await vi.waitFor(() => expect(state.data.value).toBe('count: 1'))

    dataParameters.value = { dimension: 'hosts' }
    await nextTick()

    expect(fetchResponse).toHaveBeenCalledTimes(1)
  })

  it('reports a backend-reported condition as a warning, using its message', async () => {
    const fetchResponse = vi
      .fn()
      .mockRejectedValue(new CmkApiError('Flow monitoring is disabled', null, ''))

    const state = renderHarness(fetchResponse)

    await vi.waitFor(() =>
      expect(state.error.value).toEqual({
        variant: 'warning',
        message: 'Flow monitoring is disabled'
      })
    )
    expect(state.data.value).toBeUndefined()
  })

  it('reports an unexpected failure as an error, with a generic message', async () => {
    const fetchResponse = vi.fn().mockRejectedValue(new Error('boom'))

    const state = renderHarness(fetchResponse)

    await vi.waitFor(() => expect(state.error.value?.variant).toBe('error'))
    expect(state.error.value?.message).not.toBe('boom')
  })

  it('keeps rendering the previous data while a refetch is in flight', async () => {
    let resolveSecond: (response: Response) => void = () => {}
    const fetchResponse = vi
      .fn()
      .mockResolvedValueOnce({ count: 1 })
      .mockReturnValueOnce(
        new Promise<Response>((resolve) => {
          resolveSecond = resolve
        })
      )
    const dataParameters = ref<unknown>({ dimension: 'hosts' })

    const state = renderHarness(fetchResponse, dataParameters)
    await vi.waitFor(() => expect(state.data.value).toBe('count: 1'))

    dataParameters.value = { dimension: 'autonomous_systems' }
    await nextTick()
    // Not back to undefined: the widget would flicker into its loading state.
    expect(state.data.value).toBe('count: 1')

    resolveSecond({ count: 2 })
    await vi.waitFor(() => expect(state.data.value).toBe('count: 2'))
  })

  it('ignores a stale response that resolves after a newer one', async () => {
    let resolveFirst: (response: Response) => void = () => {}
    const fetchResponse = vi
      .fn()
      .mockReturnValueOnce(
        new Promise<Response>((resolve) => {
          resolveFirst = resolve
        })
      )
      .mockResolvedValueOnce({ count: 2 })
    const dataParameters = ref<unknown>({ dimension: 'hosts' })

    const state = renderHarness(fetchResponse, dataParameters)
    dataParameters.value = { dimension: 'autonomous_systems' }
    await nextTick()
    await vi.waitFor(() => expect(state.data.value).toBe('count: 2'))

    resolveFirst({ count: 1 })
    await nextTick()

    expect(state.data.value).toBe('count: 2')
  })

  it('keeps the error state until a request actually succeeds', async () => {
    let resolveSecond: (response: Response) => void = () => {}
    const fetchResponse = vi
      .fn()
      .mockRejectedValueOnce(new CmkApiError('Database unreachable', null, ''))
      .mockReturnValueOnce(
        new Promise<Response>((resolve) => {
          resolveSecond = resolve
        })
      )
    const dataParameters = ref<unknown>({ dimension: 'hosts' })

    const state = renderHarness(fetchResponse, dataParameters)
    await vi.waitFor(() => expect(state.error.value?.message).toBe('Database unreachable'))

    dataParameters.value = { dimension: 'autonomous_systems' }
    await nextTick()
    // Still failing as far as the widget knows, so it keeps showing the alert.
    expect(state.error.value?.message).toBe('Database unreachable')

    resolveSecond({ count: 2 })
    await vi.waitFor(() => expect(state.error.value).toBeNull())
    expect(state.data.value).toBe('count: 2')
  })

  describe('auto-reload', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('reloads at the refresh interval', async () => {
      const fetchResponse = vi.fn().mockResolvedValue({ count: 1 })

      renderHarness(fetchResponse)
      await vi.advanceTimersByTimeAsync(0)
      expect(fetchResponse).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(NETWORK_FLOW_REFRESH_INTERVAL_MS)
      expect(fetchResponse).toHaveBeenCalledTimes(2)

      await vi.advanceTimersByTimeAsync(NETWORK_FLOW_REFRESH_INTERVAL_MS)
      expect(fetchResponse).toHaveBeenCalledTimes(3)
    })

    it('keeps the previous data across a reload', async () => {
      const fetchResponse = vi
        .fn()
        .mockResolvedValueOnce({ count: 1 })
        .mockResolvedValueOnce({ count: 2 })

      const state = renderHarness(fetchResponse)
      await vi.advanceTimersByTimeAsync(0)
      expect(state.data.value).toBe('count: 1')

      await vi.advanceTimersByTimeAsync(NETWORK_FLOW_REFRESH_INTERVAL_MS)
      expect(state.data.value).toBe('count: 2')
    })

    it('skips reloading while the document is hidden', async () => {
      const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
      const fetchResponse = vi.fn().mockResolvedValue({ count: 1 })

      renderHarness(fetchResponse)
      await vi.advanceTimersByTimeAsync(0)
      expect(fetchResponse).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(NETWORK_FLOW_REFRESH_INTERVAL_MS * 3)
      expect(fetchResponse).toHaveBeenCalledTimes(1)

      // Becoming visible again reloads right away instead of waiting out the
      // rest of the interval.
      hidden.mockReturnValue(false)
      document.dispatchEvent(new Event('visibilitychange'))
      await vi.advanceTimersByTimeAsync(0)
      expect(fetchResponse).toHaveBeenCalledTimes(2)
    })

    it('stops reloading once the widget is unmounted', async () => {
      const fetchResponse = vi.fn().mockResolvedValue({ count: 1 })

      const state = renderHarness(fetchResponse)
      await vi.advanceTimersByTimeAsync(NETWORK_FLOW_REFRESH_INTERVAL_MS)
      expect(fetchResponse).toHaveBeenCalledTimes(2)

      state.unmount()
      await vi.advanceTimersByTimeAsync(NETWORK_FLOW_REFRESH_INTERVAL_MS * 3)

      expect(fetchResponse).toHaveBeenCalledTimes(2)
    })

    it('does not restart the timer when a request resolves after unmount', async () => {
      let resolvePending: (response: Response) => void = () => {}
      const fetchResponse = vi.fn().mockReturnValue(
        new Promise<Response>((resolve) => {
          resolvePending = resolve
        })
      )

      const state = renderHarness(fetchResponse)
      state.unmount()

      resolvePending({ count: 1 })
      await vi.advanceTimersByTimeAsync(NETWORK_FLOW_REFRESH_INTERVAL_MS * 3)

      expect(fetchResponse).toHaveBeenCalledTimes(1)
      expect(state.data.value).toBeUndefined()
    })
  })
})
