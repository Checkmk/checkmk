/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import DashboardContentGraph from '@/dashboard/components/DashboardContent/DashboardContentGraph.vue'

// jsdom has no ResizeObserver and does no layout. The widget only requests its graph once the
// observer reports a size, so keep a handle on the callback to drive that.
let resizeCallback: ResizeObserverCallback | null = null
class FakeResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    resizeCallback = callback
  }
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

// The graph body arrives through the legacy cmk ajax toolkit as raw HTML. Capturing the response
// handler lets a test replay the moment it lands, which is what clears the loading flag; the error
// handler drives the failure path, and the count tells whether a retry issued a fresh request.
let respond: ((data: null, body: string) => void) | null = null
let fail: (() => void) | null = null
let requestCount = 0

const baseProps = {
  widget_id: 'w1',
  general_settings: {
    title: { text: 'CPU utilization', render_mode: 'with_background' as const },
    render_background: true
  },
  content: {
    type: 'performance_graph',
    graph_render_options: { show_legend: false, show_graph_time: false }
  },
  effectiveTitle: 'CPU utilization',
  effective_filter_context: { uses_infos: [], filters: {}, context: {} },
  dashboardKey: { owner: 'cmkadmin', name: 'main' }
}

const loadingIcon = (): Element | null => document.querySelector('.db-content-graph__loading-icon')

const graphBody = (): Element | null => document.querySelector('.db-content-graph')

function renderWidget() {
  return render(DashboardContentGraph, { props: baseProps as never })
}

// Report a size, then let the 300ms debounce elapse so the widget issues its ajax request.
async function deliverSize(): Promise<void> {
  resizeCallback!(
    [{ contentBoxSize: [{ inlineSize: 400, blockSize: 200 }] }] as never,
    null as never
  )
  await nextTick()
  await vi.advanceTimersByTimeAsync(300)
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
  vi.stubGlobal('cmk', {
    ajax: {
      call_ajax: (
        _url: string,
        opts: {
          response_handler: (data: null, body: string) => void
          error_handler: () => void
        }
      ) => {
        requestCount += 1
        respond = opts.response_handler
        fail = opts.error_handler
      }
    },
    utils: { execute_javascript_by_object: () => {} }
  })
})

afterEach(() => {
  respond = null
  fail = null
  requestCount = 0
  resizeCallback = null
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

test('holds the loading icon back for a second while the graph is loading', async () => {
  renderWidget()

  await nextTick()
  expect(loadingIcon()).not.toBeVisible()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon()).toBeVisible()
})

test('a fast render never shows the loading icon', async () => {
  renderWidget()
  await nextTick()
  await deliverSize()

  respond!(null, '<svg />')
  await nextTick()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon()).not.toBeVisible()
})

test('keeps the graph hidden from the start, undelayed, until it has rendered', async () => {
  renderWidget()
  await nextTick()
  await deliverSize()

  expect(graphBody()).not.toBeVisible()

  respond!(null, '<svg />')
  await nextTick()
  expect(graphBody()).toBeVisible()
})

test('states the failure and stops the loading icon when the request errors', async () => {
  renderWidget()
  await nextTick()
  await deliverSize()

  fail!()
  await nextTick()

  expect(screen.getByText('Graph data could not be loaded.')).toBeInTheDocument()
  // Regression: the icon used to keep spinning, because only the refresh timer was told.
  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon()).not.toBeVisible()
})

test('retrying issues a fresh request and clears the notice once it lands', async () => {
  renderWidget()
  await nextTick()
  await deliverSize()
  fail!()
  await nextTick()

  const before = requestCount
  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  expect(requestCount).toBe(before + 1)

  respond!(null, '<svg />')
  await nextTick()

  expect(screen.queryByText('Graph data could not be loaded.')).not.toBeInTheDocument()
  expect(graphBody()).toBeVisible()
})

test('acknowledges a retry at once rather than blanking the widget', async () => {
  renderWidget()
  await nextTick()
  await deliverSize()
  fail!()
  await nextTick()

  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

  // No waiting out LOADING_AFFORDANCE_DELAY_MS: the notice holds the wait immediately.
  expect(screen.getByText('Loading data …')).toBeInTheDocument()
  expect(loadingIcon()).not.toBeVisible()
})
