/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import DashboardContentGraph from '@/dashboard/components/DashboardContent/DashboardContentGraph.vue'

// jsdom has no ResizeObserver and does no layout. A widget only requests its graph once the
// observer reports a size, so keep the callbacks to drive that - one per widget on screen.
let resizeCallbacks: ResizeObserverCallback[] = []
class FakeResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    resizeCallbacks.push(callback)
  }
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

// The graph body arrives through the legacy cmk ajax toolkit as raw HTML. Capturing the response
// handler lets a test replay the moment it lands, which is what clears the loading flag; the error
// handler drives the failure path, and the count tells whether a retry issued a fresh request.
//
// Kept per widget, not once: the containment tests put two on screen, and a single handle would
// leave the second overwriting the first's.
interface WidgetAjax {
  respond: (data: null, body: string) => void
  fail: () => void
  requests: number
}
const ajaxByWidget = new Map<string, WidgetAjax>()

function ajax(widgetId = 'w1'): WidgetAjax {
  const entry = ajaxByWidget.get(widgetId)
  if (entry === undefined) {
    throw new Error(`Widget "${widgetId}" has not requested its graph yet`)
  }
  return entry
}

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

// Scoped to a root so the two-widget tests can ask about one widget rather than the document.
const loadingIcon = (root: ParentNode = document): Element | null =>
  root.querySelector('.db-content-graph__loading-icon')

const graphBody = (root: ParentNode = document): Element | null =>
  root.querySelector('.db-content-graph')

const notice = (root: ParentNode = document): Element | null =>
  root.querySelector('.graphing-graph-notice')

const skeletons = (root: ParentNode = document): NodeListOf<Element> =>
  root.querySelectorAll('.graphing-graph-skeleton')

// Each render gets its own container, which is what scopes the queries above per widget.
function renderWidget(widgetId = 'w1'): HTMLElement {
  return render(DashboardContentGraph, {
    props: { ...baseProps, widget_id: widgetId } as never
  }).container as HTMLElement
}

// Report a size to every widget on screen, then let the 300ms debounce elapse so they issue their
// ajax requests.
async function deliverSize(): Promise<void> {
  for (const callback of resizeCallbacks) {
    callback([{ contentBoxSize: [{ inlineSize: 400, blockSize: 200 }] }] as never, null as never)
  }
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
          post_data: string
          response_handler: (data: null, body: string) => void
          error_handler: () => void
        }
      ) => {
        // The widget names itself in the request body, which is the only thing distinguishing
        // two widgets' calls through this one toolkit entry point.
        const widgetId = new URLSearchParams(opts.post_data).get('widget_id')!
        ajaxByWidget.set(widgetId, {
          respond: opts.response_handler,
          fail: opts.error_handler,
          requests: (ajaxByWidget.get(widgetId)?.requests ?? 0) + 1
        })
      }
    },
    utils: { execute_javascript_by_object: () => {} }
  })
})

afterEach(() => {
  ajaxByWidget.clear()
  resizeCallbacks = []
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
  // Containment picks the affordance: a widget spins, only a page skeletonises its panels.
  expect(skeletons()).toHaveLength(0)
})

test('a fast render never shows the loading icon', async () => {
  renderWidget()
  await nextTick()
  await deliverSize()

  ajax().respond(null, '<svg />')
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

  ajax().respond(null, '<svg />')
  await nextTick()
  expect(graphBody()).toBeVisible()
})

test('states the failure and stops the loading icon when the request errors', async () => {
  renderWidget()
  await nextTick()
  await deliverSize()

  ajax().fail()
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
  ajax().fail()
  await nextTick()

  const before = ajax().requests
  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  expect(ajax().requests).toBe(before + 1)

  ajax().respond(null, '<svg />')
  await nextTick()

  expect(screen.queryByText('Graph data could not be loaded.')).not.toBeInTheDocument()
  expect(graphBody()).toBeVisible()
})

test('acknowledges a retry at once rather than blanking the widget', async () => {
  renderWidget()
  await nextTick()
  await deliverSize()
  ajax().fail()
  await nextTick()

  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

  // No waiting out LOADING_AFFORDANCE_DELAY_MS: the notice holds the wait immediately.
  expect(screen.getByText('Loading data …')).toBeInTheDocument()
  expect(loadingIcon()).not.toBeVisible()
})

test('each widget spins and resolves on its own request, not the dashboard as a whole', async () => {
  const first = renderWidget('w1')
  const second = renderWidget('w2')
  await nextTick()
  await deliverSize()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon(first)).toBeVisible()
  expect(loadingIcon(second)).toBeVisible()

  ajax('w1').respond(null, '<svg />')
  await nextTick()

  expect(loadingIcon(first)).not.toBeVisible()
  expect(graphBody(first)).toBeVisible()
  // The one still in flight is untouched by its neighbour arriving.
  expect(loadingIcon(second)).toBeVisible()
  expect(graphBody(second)).not.toBeVisible()
})

test("a widget's failure stays in its own frame, with the retry that belongs to it", async () => {
  const first = renderWidget('w1')
  const second = renderWidget('w2')
  await nextTick()
  await deliverSize()

  ajax('w1').fail()
  ajax('w2').respond(null, '<svg />')
  await nextTick()

  expect(within(first).getByText('Graph data could not be loaded.')).toBeVisible()
  expect(notice(second)).not.toBeInTheDocument()
  expect(graphBody(second)).toBeVisible()

  const before = ajax('w2').requests
  await fireEvent.click(within(first).getByRole('button', { name: 'Retry' }))

  // The retry refetches the widget it sits in and leaves the healthy one alone.
  expect(ajax('w1').requests).toBe(2)
  expect(ajax('w2').requests).toBe(before)
})
