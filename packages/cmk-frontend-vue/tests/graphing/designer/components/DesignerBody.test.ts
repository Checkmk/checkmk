/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import type { CustomGraphObject } from '@/graphing/designer/api'
import DesignerBody from '@/graphing/designer/components/DesignerBody.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { fromApiDataSource } from '@/graphing/designer/drafts'

vi.mock('cmk-ui-library/components/CmkSlideIn/CmkSlideIn.vue', () => ({
  default: defineComponent({
    name: 'CmkSlideIn',
    props: { open: { type: Boolean, required: true } },
    setup(props, { slots }) {
      return () => (props.open ? h('div', { 'data-testid': 'slide-in' }, slots.default?.()) : null)
    }
  })
}))

vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: {
    inheritAttrs: false,
    props: ['metrics', 'highlightedMetricName'],
    template: `<div data-testid="time-series-graph">
      <span data-testid="drawn">{{ metrics.map((m) => m.metadata.title).join(',') }}</span>
      <span data-testid="highlighted">{{ highlightedMetricName ?? '' }}</span>
    </div>`
  }
}))

vi.mock('@/graphing/api/graphPin', () => ({
  loadGraphPin: () => Promise.resolve(null),
  saveGraphPin: () => Promise.resolve()
}))

const PALETTE = ['#28a2f3', '#ff8400']

function rrdSource(id: string): unknown {
  return {
    type: 'rrd_metric',
    id,
    title: id,
    line_type: 'line',
    mirrored: false,
    visible: true,
    color: '#28a2f3',
    host_name: 'my-host',
    service_name: 'CPU utilization',
    metric_name: 'util',
    consolidation: 'avg'
  }
}

function graphObject(dataSources: unknown[] = [rrdSource('A'), rrdSource('B')]): CustomGraphObject {
  return {
    domainType: 'custom_graph',
    id: 'my_graph',
    title: 'My graph',
    links: [],
    extensions: {
      owner: 'me',
      is_editable: true,
      metadata: {
        description: '',
        topic: 'my_workplace',
        sort_index: 99,
        hidden: false,
        is_show_more: false,
        public: { type: 'private' }
      },
      content: {
        graph_options: {
          unit: { type: 'first_entry_with_unit' },
          explicit_vertical_range: { type: 'auto' },
          omit_zero_metrics: false
        },
        data_sources: dataSources
      }
    }
  } as unknown as CustomGraphObject
}

function metric(sourceId: string, name: string, title: string): unknown {
  return {
    source_id: sourceId,
    metadata: {
      name,
      title,
      unit: {
        notation: 'decimal',
        symbol: '',
        precision: { type: 'auto', digits: 2 },
        convertible: false
      },
      color: '#28a2f3'
    },
    render: { stack: null, inverse: false, hidden: false },
    data_points: [1, 2]
  }
}

/** The fetch_data POST returns two series, one per (visible) data source. */
function fetchDataResponse(): unknown {
  return {
    data: {
      time_range: { start: 0, end: 3600, step: 60 },
      metrics: [metric('A', 'metric-a', 'CPU'), metric('B', 'metric-b', 'Memory')],
      group_titles: [],
      horizontal_lines: [],
      warnings: [],
      errors: []
    },
    error: undefined,
    response: new Response(null, { status: 200 })
  }
}

beforeEach(() => {
  vi.spyOn(client, 'POST').mockResolvedValue(fetchDataResponse())
})

afterEach(() => {
  vi.restoreAllMocks()
})

function bodyProps(graph: CustomGraphObject = graphObject()) {
  return {
    store: useGraphItems(PALETTE, graph.extensions.content.data_sources.map(fromApiDataSource)),
    graphOptions: graph.extensions.content.graph_options,
    title: 'My graph',
    mode: 'edit' as 'view' | 'edit',
    thresholds: { warning: '#ffd000', critical: '#ff3232' },
    metricBackendAvailable: false,
    createServicesAvailable: true,
    metricBackendDefaultTitle: '$METRIC_NAME$ - $SERIES_ID$',
    titleMacros: []
  }
}

function renderBody(
  mode: 'view' | 'edit',
  overrides: { displaySettings?: boolean; graph?: CustomGraphObject } = {}
) {
  const { graph, ...rest } = overrides
  return render(DesignerBody, { props: { ...bodyProps(graph), mode, ...rest } })
}

test('hiding a metric in the detached view-mode legend removes it from the preview', async () => {
  renderBody('view')

  const chart = await screen.findByTestId('time-series-graph')
  await waitFor(() => expect(chart).toHaveTextContent('CPU'))
  expect(chart).toHaveTextContent('Memory')

  await fireEvent.click(screen.getByRole('button', { name: 'CPU' }))
  await waitFor(() => expect(chart).not.toHaveTextContent('CPU'))
  expect(chart).toHaveTextContent('Memory')
})

test('hovering a metric in the detached legend highlights it in the preview', async () => {
  renderBody('view')

  await waitFor(() => expect(screen.getByTestId('drawn')).toHaveTextContent('CPU'))
  expect(screen.getByTestId('highlighted').textContent).toBe('')

  const cpuRow = screen.getByText('CPU').closest('tr')!
  await fireEvent.mouseEnter(cpuRow)
  expect(screen.getByTestId('highlighted')).toHaveTextContent('metric-a')

  await fireEvent.mouseLeave(cpuRow)
  expect(screen.getByTestId('highlighted').textContent).toBe('')
})

test('view mode renders the legend beneath the preview, not the config tabs', async () => {
  const { container } = renderBody('view')

  await waitFor(() => expect(screen.getByTestId('time-series-graph')).toHaveTextContent('CPU'))
  expect(container.querySelector('.graphing-graph-legend')).not.toBeNull()
  expect(screen.queryByRole('tab')).toBeNull()
})

test('edit mode renders the config tabs beneath the preview, not the legend', async () => {
  const { container } = renderBody('edit')

  expect(await screen.findByRole('tab', { name: 'Graph appearance' })).toBeInTheDocument()
  expect(screen.getByRole('tab', { name: 'Metrics selection' })).toBeInTheDocument()
  expect(container.querySelector('.graphing-graph-legend')).toBeNull()
})

describe('settings slide-out', () => {
  test('is closed by default', () => {
    renderBody('edit')

    expect(screen.queryByRole('heading', { name: 'Custom graph settings' })).not.toBeInTheDocument()
  })

  test('opens when displaySettings is set, reflecting the current graph options', async () => {
    renderBody('edit', { displaySettings: true })

    expect(
      await screen.findByRole('heading', { name: 'Custom graph settings' })
    ).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Show zero values' })).toBeChecked()
  })

  test('accepting a change closes the panel and hands the edited options up', async () => {
    const { emitted } = renderBody('edit', { displaySettings: true })

    await fireEvent.click(await screen.findByRole('checkbox', { name: 'Show zero values' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    // DesignerBody's onSettingsUpdate closes the panel via the displaySettings v-model.
    expect(emitted()['update:displaySettings']).toEqual([[false]])
    expect(emitted()['update-graph-options']).toEqual([
      [expect.objectContaining({ omit_zero_metrics: true })]
    ])
  })

  test('cancelling discards the change instead of handing it up', async () => {
    const { emitted } = renderBody('edit', { displaySettings: true })

    await fireEvent.click(await screen.findByRole('checkbox', { name: 'Show zero values' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(emitted()['update:displaySettings']).toEqual([[false]])
    expect(emitted()['update-graph-options']).toBeUndefined()
  })
})

test('states a failed preview fetch over the preview, offering a retry', async () => {
  const postSpy = vi.spyOn(client, 'POST')
  postSpy.mockRejectedValue(new Error('crash'))
  renderBody('view')

  expect(await screen.findByText('Graph data could not be loaded.')).toBeInTheDocument()
  expect(screen.getByText('crash')).toBeInTheDocument()

  postSpy.mockResolvedValue(fetchDataResponse())
  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

  await waitFor(() =>
    expect(screen.queryByText('Graph data could not be loaded.')).not.toBeInTheDocument()
  )
  expect(await screen.findByTestId('time-series-graph')).toBeInTheDocument()
})

test("states the response's own per-metric errors without offering a retry", async () => {
  const response = fetchDataResponse() as { data: Record<string, unknown> }
  vi.spyOn(client, 'POST').mockResolvedValue({
    ...response,
    data: { ...response.data, errors: ['Metrics backend is unavailable.'] }
  } as never)
  renderBody('view')

  expect(await screen.findByText('Metrics backend is unavailable.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
})

test("states the response's own warnings over the preview it drew anyway", async () => {
  const response = fetchDataResponse() as { data: Record<string, unknown> }
  vi.spyOn(client, 'POST').mockResolvedValue({
    ...response,
    data: { ...response.data, warnings: ['The query for A matched more than 100 time series.'] }
  } as never)
  renderBody('view')

  const message = await screen.findByText('The query for A matched more than 100 time series.')
  expect(message.closest('.graphing-graph-notice')).toHaveClass('graphing-graph-notice--warning')
  expect(await screen.findByTestId('time-series-graph')).toBeInTheDocument()
})

test('states an empty custom graph over a drawn frame', async () => {
  renderBody('view', { graph: graphObject([]) })

  expect(await screen.findByText('No metrics added')).toBeInTheDocument()
  expect(screen.getByText('Add a source to visualize your data')).toBeInTheDocument()
  // The frame is drawn even with nothing to plot, so the notice has a graph to sit over.
  expect(screen.getByTestId('time-series-graph')).toBeInTheDocument()
  // An empty graph is not a failure: nothing to retry.
  expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
})

test('says nothing about emptiness once a source has been added', async () => {
  renderBody('view')

  expect(await screen.findByTestId('time-series-graph')).toBeInTheDocument()
  expect(screen.queryByText('No metrics added')).not.toBeInTheDocument()
})
