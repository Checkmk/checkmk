/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import DashboardContentTimeSeriesGraph from '@/dashboard/components/DashboardContent/DashboardContentTimeSeriesGraph.vue'
import type { CustomGraphContent } from '@/dashboard/types/widget.ts'

// The figure owns its own data fetch; stubbing it keeps these tests on the discovery step.
vi.mock('@/graphing/components/GraphFigure/GraphFigure.vue', () => ({
  default: {
    props: ['internal', 'timerange', 'combinationMode', 'showLegend', 'showTimestamp'],
    template: '<div data-testid="graph-figure">{{ internal }}</div>'
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
