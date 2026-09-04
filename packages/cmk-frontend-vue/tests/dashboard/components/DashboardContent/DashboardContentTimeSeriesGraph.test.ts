/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import DashboardContentTimeSeriesGraph from '@/dashboard/components/DashboardContent/DashboardContentTimeSeriesGraph.vue'
import { createSharedGraphFetcher } from '@/dashboard/components/DashboardContent/sharedGraphFetcher'
import { useProvideCmkToken } from '@/dashboard/composables/useCmkToken'
import { useProvideSharedWidgetGraphs } from '@/dashboard/composables/useSharedWidgetGraphs'
import type { SharedWidgetGraphs } from '@/dashboard/types/page.ts'
import type { CustomGraphContent } from '@/dashboard/types/widget.ts'

// The figure owns its own data fetch; stubbing it keeps these tests on the discovery step and on
// which fetch function the widget hands it.
vi.mock('@/graphing/components/GraphFigure/GraphFigure.vue', () => ({
  default: {
    props: [
      'internal',
      'timerange',
      'combinationMode',
      'showLegend',
      'showTimestamp',
      'showPin',
      'showTimeAxis',
      'showValueAxis',
      'showMargin',
      'minValueAxisWidth',
      'fetchGraph'
    ],
    template: `<div
      data-testid="graph-figure"
      :data-show-pin="showPin"
      :data-has-fetch-graph="fetchGraph !== undefined"
      :data-show-time-axis="showTimeAxis"
      :data-show-value-axis="showValueAxis"
      :data-show-margin="showMargin"
      :data-min-value-axis-width="minValueAxisWidth"
    >{{ internal }}</div>`
  }
}))

const CUSTOM_GRAPH_CONTENT: CustomGraphContent = {
  type: 'custom_graph',
  custom_graph: 'my_graph',
  timerange: { type: 'predefined', value: 'last_25_hours' },
  graph_render_options: { show_legend: true, show_graph_time: false }
}

const baseProps = {
  widget_id: 'w1',
  general_settings: {
    title: { text: 'My graph', render_mode: 'with_background' as const },
    render_background: true
  },
  content: CUSTOM_GRAPH_CONTENT,
  effectiveTitle: 'My graph',
  effective_filter_context: { uses_infos: [], filters: {}, context: {} },
  dashboardKey: { owner: 'cmkadmin', name: 'main' }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue({
    data: { graphs: [{ internal: '{"graphs": []}', title: 'My graph' }], no_data_message: null },
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
})

afterEach(() => {
  vi.restoreAllMocks()
})

function renderWidget(props: Record<string, unknown> = {}) {
  return render(DashboardContentTimeSeriesGraph, {
    props: { ...baseProps, ...props } as never
  })
}

describe('custom graph widget', () => {
  test('discovers the custom graph by its name', async () => {
    renderWidget()

    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1))
    expect(postSpy.mock.calls[0][0]).toBe(
      '/domain-types/graph/actions/discover_custom_graphs/invoke'
    )
    expect(postSpy.mock.calls[0][1].body).toEqual({ custom_graph: 'my_graph' })
  })

  test('renders the figure with the discovered definition', async () => {
    renderWidget()

    expect(await screen.findByTestId('graph-figure')).toHaveTextContent('{"graphs": []}')
  })

  test('does not rediscover when only the dashboard filter context changes', async () => {
    const { rerender } = renderWidget()
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1))

    await rerender({
      effective_filter_context: {
        uses_infos: [],
        filters: { host: { host: 'other-host' } },
        context: {}
      }
    } as never)

    expect(postSpy).toHaveBeenCalledTimes(1)
  })

  test('rediscovers when the configured custom graph changes', async () => {
    const { rerender } = renderWidget()
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1))

    await rerender({
      content: { ...CUSTOM_GRAPH_CONTENT, custom_graph: 'other_graph' }
    } as never)

    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))
    expect(postSpy.mock.calls[1][1].body).toEqual({ custom_graph: 'other_graph' })
  })

  test('shows the error message when the graph cannot be discovered', async () => {
    postSpy.mockResolvedValue({
      data: undefined,
      error: { title: 'Custom graph not found', detail: 'No custom graph was found.' },
      response: new Response('{}', { status: 404 })
    } as never)

    renderWidget()

    expect(
      await screen.findByText(/Custom graph not found: No custom graph was found\./)
    ).toBeInTheDocument()
  })
})

describe('graph render options', () => {
  test('passes the configured axis visibility on to the figure', async () => {
    renderWidget({
      content: {
        ...CUSTOM_GRAPH_CONTENT,
        graph_render_options: { show_time_axis: false, show_vertical_axis: false }
      }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-show-time-axis')).toBe('false')
    expect(figure.getAttribute('data-show-value-axis')).toBe('false')
  })

  test('converts an absolute vertical axis width to pixels', async () => {
    renderWidget({
      content: {
        ...CUSTOM_GRAPH_CONTENT,
        graph_render_options: { vertical_axis_width: 30 }
      }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-min-value-axis-width')).toBe('40')
  })

  test('sizes a fixed vertical axis width from the graph font size', async () => {
    renderWidget({
      content: {
        ...CUSTOM_GRAPH_CONTENT,
        graph_render_options: { vertical_axis_width: 'fixed', font_size_pt: 12 }
      }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-min-value-axis-width')).toBe('96')
  })

  test('shows both axes when the widget stores no axis options', async () => {
    renderWidget({
      content: { ...CUSTOM_GRAPH_CONTENT, graph_render_options: { show_legend: true } }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-show-time-axis')).toBe('true')
    expect(figure.getAttribute('data-show-value-axis')).toBe('true')
  })

  test('a stored margin option insets the figure', async () => {
    const marginRequested = { ...CUSTOM_GRAPH_CONTENT, graph_render_options: { show_margin: true } }

    renderWidget({ content: marginRequested })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-show-margin')).toBe('true')
  })

  test('a widget storing no margin option leaves the figure flush', async () => {
    const marginUnset = { ...CUSTOM_GRAPH_CONTENT, graph_render_options: { show_legend: true } }

    renderWidget({ content: marginUnset })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-show-margin')).toBe('false')
  })
})

const CMK_TOKEN = '0:the-token'

function renderInSharedDashboard(widgetGraphs: Record<string, SharedWidgetGraphs>) {
  const wrapper = defineComponent({
    setup() {
      useProvideCmkToken(CMK_TOKEN)
      useProvideSharedWidgetGraphs(widgetGraphs)
      return () => h(DashboardContentTimeSeriesGraph, baseProps as never)
    }
  })
  return render(wrapper)
}

describe('graph widget on a shared dashboard', () => {
  test('renders the pre-discovered shell without discovering itself', async () => {
    renderInSharedDashboard({
      w1: {
        graphs: [
          {
            internal: '{"graphs": []}',
            title: 'My graph',
            name: 'my_graph',
            add_to_specification: null
          }
        ],
        no_data_message: null
      }
    })

    expect(await screen.findByTestId('graph-figure')).toHaveTextContent('{"graphs": []}')
    expect(postSpy).not.toHaveBeenCalled()
  })

  test('shows the backend explanation when nothing was discovered', async () => {
    renderInSharedDashboard({
      w1: { graphs: [], no_data_message: 'The service has no matching graphs.' }
    })

    expect(await screen.findByText('The service has no matching graphs.')).toBeInTheDocument()
    expect(screen.queryByTestId('graph-figure')).not.toBeInTheDocument()
  })

  test('shows the discovery error of a widget the backend could not resolve', async () => {
    renderInSharedDashboard({ w1: { error: 'Host not found' } })

    expect(await screen.findByText('Host not found')).toBeInTheDocument()
  })

  test('reports widgets missing from the pre-discovered shells', async () => {
    renderInSharedDashboard({})

    expect(await screen.findByText('This graph could not be resolved.')).toBeInTheDocument()
  })

  test('hands the figure a fetch function instead of letting it fetch by definition', async () => {
    renderInSharedDashboard({
      w1: {
        graphs: [
          {
            internal: '{"graphs": []}',
            title: 'My graph',
            name: 'my_graph',
            add_to_specification: null
          }
        ],
        no_data_message: null
      }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-has-fetch-graph')).toBe('true')
  })
})

describe('createSharedGraphFetcher', () => {
  test('fetches by widget ID with the dashboard token, never by graph definition', async () => {
    postSpy.mockResolvedValue({
      data: {
        title: 'CPU utilization',
        metrics: [],
        time_range: { start: 1_000, end: 2_000, step: 60 },
        horizontal_lines: [],
        warnings: [],
        errors: []
      },
      error: undefined,
      response: new Response('{}', { status: 200 })
    } as never)

    const fetched = await createSharedGraphFetcher('w1', CMK_TOKEN)(
      { internal: '{"graphs": []}' },
      {
        fetchWindow: { start: 1_000, end: 2_000, step: 60 },
        consolidationFunction: 'max',
        combinationMode: null
      }
    )

    // The body is matched exactly: the graph definition must not be part of it.
    expect(postSpy).toHaveBeenCalledWith(
      '/domain-types/dashboard/actions/fetch-widget-graph-data/invoke',
      expect.objectContaining({
        headers: { Authorization: `CMK-TOKEN ${CMK_TOKEN}` },
        body: {
          widget_id: 'w1',
          requested_time_range: { start: 1_000, end: 2_000, step: 60 },
          consolidation_function: 'max'
        }
      })
    )
    expect(fetched.timeRange).toEqual({ start: 1_000, end: 2_000, step: 60 })
  })
})

describe('the widget pin', () => {
  const pinOf = async (): Promise<string | null> =>
    (await screen.findByTestId('graph-figure')).getAttribute('data-show-pin')

  test('is armed by default, matching the wizard default', async () => {
    renderWidget()

    expect(await pinOf()).toBe('true')
  })

  // A preview is a thumbnail, not something to interact with.
  test('is never armed in the widget preview', async () => {
    renderWidget({ isPreview: true })

    expect(await pinOf()).toBe('false')
  })
})
