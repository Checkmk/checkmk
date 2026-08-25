/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, toZoned } from '@internationalized/date'
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

import { useGlobalTimeRange } from '@/graphing/GlobalTimePicker/useGlobalTimeRange'
import type { CustomGraphObject } from '@/graphing/designer/api'
import DesignerBody from '@/graphing/designer/components/DesignerBody.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { fromApiDataSource } from '@/graphing/designer/drafts'
import type { ApiDataSource, ApiDataSourceInput, ItemId } from '@/graphing/designer/types'
import type { RowIssue } from '@/graphing/designer/validation'

import { filterDefinitions, metricBackendItem } from '../fixtures'

vi.mock('cmk-ui-library/components/CmkSlideIn/CmkSlideIn.vue', () => ({
  default: defineComponent({
    name: 'CmkSlideIn',
    props: { open: { type: Boolean, required: true } },
    setup(props, { slots }) {
      return () => (props.open ? h('div', { 'data-testid': 'slide-in' }, slots.default?.()) : null)
    }
  })
}))

const PAN_SECONDS = 1800
const PAN_REFETCH_TIMEOUT_MS = 2000
const PAST_WINDOW: DateTimeRange = {
  from: toZoned(new CalendarDateTime(2026, 3, 15, 10, 0), 'Europe/Berlin', 'compatible'),
  to: toZoned(new CalendarDateTime(2026, 3, 15, 11, 0), 'Europe/Berlin', 'compatible')
}

vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: {
    inheritAttrs: false,
    props: ['metrics', 'highlightedMetricName', 'panEnabled', 'view_time_range'],
    emits: ['pan'],
    template: `<div data-testid="time-series-graph">
      <span data-testid="drawn">{{ metrics.map((m) => m.metadata.title).join(',') }}</span>
      <span data-testid="highlighted">{{ highlightedMetricName ?? '' }}</span>
      <span data-testid="pan-enabled">{{ panEnabled }}</span>
      <button
        data-testid="pan-back"
        @click="$emit('pan', {
          timeRange: {
            start: view_time_range.start - PAN_SECONDS,
            end: view_time_range.end - PAN_SECONDS,
            step: view_time_range.step
          }
        })"
      />
    </div>`,
    setup: () => ({ PAN_SECONDS })
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

function rrdQuerySource(id: string): unknown {
  return {
    type: 'rrd_query',
    id,
    title: id,
    line_type: 'line',
    mirrored: false,
    visible: true,
    context: {
      hostregex: { host_regex: 'my-host' },
      serviceregex: { service_regex: 'CPU utilization' }
    },
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
  useGlobalTimeRange().setActiveTimeRange(null, 'time_picker')
  vi.spyOn(client, 'POST').mockResolvedValue(fetchDataResponse())
})

afterEach(() => {
  vi.restoreAllMocks()
})

function echoingPostSpy() {
  const postSpy = vi.spyOn(client, 'POST')
  postSpy.mockImplementation(async (_path: unknown, options: unknown) => {
    const response = fetchDataResponse() as { data: Record<string, unknown> }
    const { requested_time_range: requested } = (
      options as { body: { requested_time_range: unknown } }
    ).body
    return { ...response, data: { ...response.data, time_range: requested } } as never
  })
  return postSpy
}

function requestedRangeOf(call: unknown[]): { start: number; end: number; step: number } {
  return (
    call[1] as { body: { requested_time_range: { start: number; end: number; step: number } } }
  ).body.requested_time_range
}

function bodyProps(graph: CustomGraphObject = graphObject()) {
  const store = useGraphItems(PALETTE)
  store.replaceAll(graph.extensions.content.data_sources.map(fromApiDataSource))
  return {
    store,
    graphOptions: graph.extensions.content.graph_options,
    title: 'My graph',
    mode: 'edit' as 'view' | 'edit',
    thresholds: { warning: '#ffd000', critical: '#ff3232' },
    metricBackendAvailable: false,
    createServicesAvailable: true,
    metricBackendDefaultTitle: '$METRIC_NAME$ - $SERIES_ID$',
    titleMacros: [],
    issuesByRow: new Map<ItemId, RowIssue[]>()
  }
}

function renderBody(
  mode: 'view' | 'edit',
  overrides: {
    displaySettings?: boolean
    graph?: CustomGraphObject
    issuesByRow?: ReadonlyMap<ItemId, RowIssue[]>
    metricBackendAvailable?: boolean
  } = {}
) {
  const { graph, ...rest } = overrides
  const props = { ...bodyProps(graph), mode, ...rest }
  const events = {
    'onUpdate:displaySettings': vi.fn(),
    onUpdateGraphOptions: vi.fn()
  }
  const harness = defineComponent({
    setup() {
      useProvideFilterDefinitions({ definitions: filterDefinitions, groups: {} })
      return () => h(DesignerBody, { ...props, ...events })
    }
  })
  return { ...render(harness), props, events }
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

test('a source the rules reject is left out of the preview request', async () => {
  const postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue(fetchDataResponse())
  const outOfRange = metricBackendItem('B', {
    consolidation_function: { type: 'histogram_quantile', lookback_seconds: 300, percentile: 500 }
  })
  renderBody('edit', { graph: graphObject([rrdSource('A'), outOfRange]) })

  await waitFor(() => expect(postSpy).toHaveBeenCalled())

  const sent = postSpy.mock.calls[0]![1] as {
    body: { content: { data_sources: { id: string }[] } }
  }
  expect(sent.body.content.data_sources.map((source) => source.id)).toEqual(['A'])
})

test('edit mode renders the config tabs beneath the preview, not the legend', async () => {
  const { container } = renderBody('edit')

  expect(await screen.findByRole('tab', { name: 'Graph appearance' })).toBeInTheDocument()
  expect(screen.getByRole('tab', { name: 'Metrics selection' })).toBeInTheDocument()
  expect(container.querySelector('.graphing-graph-legend')).toBeNull()
})

test('a blocked source marks the metrics tab, from whichever tab is open', async () => {
  renderBody('edit', {
    issuesByRow: new Map([['A', [{ id: 'A', field: 'title', code: 'required' }]]])
  })
  await userEvent.click(await screen.findByRole('tab', { name: 'Graph appearance' }))

  const metrics = screen.getByRole('tab', { name: 'Metrics selection' })

  expect(metrics.querySelector('.cmk-icon')).not.toBeNull()
  expect(
    screen.getByRole('tab', { name: 'Graph appearance' }).querySelector('.cmk-icon')
  ).toBeNull()
})

test('the metrics tab names a row by what the fetch resolved it to', async () => {
  const response = fetchDataResponse() as { data: Record<string, unknown> }
  vi.spyOn(client, 'POST').mockResolvedValue({
    ...response,
    data: {
      ...response.data,
      metrics: [metric('A', 'metric-a', 'CPU'), metric('Q', 'metric-q', 'CPU of my-host')],
      group_titles: [{ source_id: 'Q', title: 'util - <HOST_NAME>/<SERVICE_DESCRIPTION>' }]
    }
  } as never)
  renderBody('edit', { graph: graphObject([rrdSource('A'), rrdQuerySource('Q')]) })

  const metricsTab = await screen.findByRole('tabpanel')
  await waitFor(() => expect(within(metricsTab).getByText('CPU')).toBeInTheDocument())
  // Q fanned out to a single series, yet a group row is named by its group title.
  expect(
    within(metricsTab).getByText('util - <HOST_NAME>/<SERVICE_DESCRIPTION>')
  ).toBeInTheDocument()
  expect(within(metricsTab).queryByText('CPU of my-host')).not.toBeInTheDocument()
})

test('a row keeps the name of the last fetch until the one its edit triggers lands', async () => {
  const response = fetchDataResponse() as { data: Record<string, unknown> }
  vi.spyOn(client, 'POST').mockResolvedValue({
    ...response,
    data: {
      ...response.data,
      metrics: [metric('A', 'metric-a', 'CPU'), metric('Q', 'metric-q', 'CPU of my-host')],
      group_titles: [{ source_id: 'Q', title: 'util - <HOST_NAME>/<SERVICE_DESCRIPTION>' }]
    }
  } as never)
  const { props } = renderBody('edit', {
    graph: graphObject([rrdSource('A'), rrdQuerySource('Q')])
  })

  const metricsTab = await screen.findByRole('tabpanel')
  await waitFor(() =>
    expect(
      within(metricsTab).getByText('util - <HOST_NAME>/<SERVICE_DESCRIPTION>')
    ).toBeInTheDocument()
  )

  props.store.replace(fromApiDataSource(rrdSource('Q') as ApiDataSourceInput))
  await nextTick()

  expect(
    within(metricsTab).getByText('util - <HOST_NAME>/<SERVICE_DESCRIPTION>')
  ).toBeInTheDocument()
  expect(within(metricsTab).queryByText('CPU of my-host')).not.toBeInTheDocument()

  await waitFor(() => expect(within(metricsTab).getByText('CPU of my-host')).toBeInTheDocument())
})

test('the metrics tab carries no marker while nothing blocks the save', async () => {
  renderBody('edit')

  const metrics = await screen.findByRole('tab', { name: 'Metrics selection' })

  expect(metrics.querySelector('.cmk-icon')).toBeNull()
})

test("a tab switch keeps each table's collapse state and the selection", async () => {
  renderBody('edit', { graph: graphObject([rrdSource('A'), rrdQuerySource('B')]) })
  await screen.findByRole('tab', { name: 'Metrics selection' })

  // The inactive panel keeps its `hidden` attribute, so role queries only see the open tab.
  const openPanel = () => screen.getByRole('tabpanel')
  const toggles = () => within(openPanel()).getAllByRole('button', { name: 'Toggle details' })
  const openTab = (name: string) => userEvent.click(screen.getByRole('tab', { name }))

  await fireEvent.click(toggles()[0]!)
  const [selectA] = within(openPanel()).getAllByLabelText('Select row')
  await fireEvent.click(selectA!)
  expect(toggles()[0]!).toHaveAttribute('aria-expanded', 'true')
  expect(toggles()[1]!).toHaveAttribute('aria-expanded', 'false')

  // Only the rrd_query row fans out into lines, and it starts open: collapse it.
  await openTab('Graph appearance')
  expect(toggles()).toHaveLength(1)
  await fireEvent.click(toggles()[0]!)
  expect(toggles()[0]!).toHaveAttribute('aria-expanded', 'false')

  await openTab('Metrics selection')
  expect(toggles()[0]!).toHaveAttribute('aria-expanded', 'true')
  expect(toggles()[1]!).toHaveAttribute('aria-expanded', 'false')
  expect(within(openPanel()).getByText('Selected rows: 1')).toBeInTheDocument()

  await openTab('Graph appearance')
  expect(toggles()[0]!).toHaveAttribute('aria-expanded', 'false')
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
    const { events } = renderBody('edit', { displaySettings: true })

    await fireEvent.click(await screen.findByRole('checkbox', { name: 'Show zero values' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    // DesignerBody's onSettingsUpdate closes the panel via the displaySettings v-model.
    expect(events['onUpdate:displaySettings'].mock.calls).toEqual([[false]])
    expect(events.onUpdateGraphOptions.mock.calls).toEqual([
      [expect.objectContaining({ omit_zero_metrics: true })]
    ])
  })

  test('cancelling discards the change instead of handing it up', async () => {
    const { events } = renderBody('edit', { displaySettings: true })

    await fireEvent.click(await screen.findByRole('checkbox', { name: 'Show zero values' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(events['onUpdate:displaySettings'].mock.calls).toEqual([[false]])
    expect(events.onUpdateGraphOptions).not.toHaveBeenCalled()
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

test.each(['view', 'edit'] as const)('the %s-mode preview arms the pan gesture', async (mode) => {
  renderBody(mode)

  expect(await screen.findByTestId('pan-enabled')).toHaveTextContent('true')
})

test('a pan on the preview refetches the shifted window, keeping its span', async () => {
  const postSpy = echoingPostSpy()
  renderBody('edit')

  await waitFor(() => expect(postSpy).toHaveBeenCalled())
  const before = requestedRangeOf(postSpy.mock.calls[0]!)

  await fireEvent.click(await screen.findByTestId('pan-back'))

  await waitFor(
    () => {
      const latest = requestedRangeOf(postSpy.mock.calls.at(-1)!)
      expect(latest).toEqual({
        start: before.start - PAN_SECONDS,
        end: before.end - PAN_SECONDS,
        step: before.step
      })
    },
    { timeout: PAN_REFETCH_TIMEOUT_MS }
  )
})

test('a pan in view mode moves the window but leaves the context view where it was', async () => {
  useGlobalTimeRange().setActiveTimeRange(PAST_WINDOW, 'time_picker')
  const postSpy = echoingPostSpy()
  renderBody('view')

  await waitFor(() => expect(postSpy.mock.calls).toHaveLength(2))
  const mainBefore = requestedRangeOf(postSpy.mock.calls[0]!)

  await fireEvent.click(await screen.findByTestId('pan-back'))

  await waitFor(() => expect(postSpy.mock.calls).toHaveLength(3), {
    timeout: PAN_REFETCH_TIMEOUT_MS
  })
  expect(requestedRangeOf(postSpy.mock.calls[2]!)).toEqual({
    start: mainBefore.start - PAN_SECONDS,
    end: mainBefore.end - PAN_SECONDS,
    step: mainBefore.step
  })
  // Only the main window was asked for again: the strip stayed where it was.
  expect(postSpy.mock.calls).toHaveLength(3)
})

/** A fetch response in which `sourceId` fanned out into one series per entry of `titles`. */
function fanOutResponse(sourceId: string, titles: string[]): unknown {
  return {
    data: {
      time_range: { start: 0, end: 3600, step: 60 },
      metrics: titles.map((title, index) => metric(sourceId, `metric-${index}`, title)),
      group_titles: [],
      horizontal_lines: [],
      warnings: [],
      errors: []
    },
    error: undefined,
    response: new Response(null, { status: 200 })
  }
}

function drawnTitles(): string {
  return screen.getByTestId('drawn').textContent!
}

function lastPostedSources(postSpy: ReturnType<typeof vi.spyOn>): ApiDataSource[] {
  const calls = postSpy.mock.calls
  const options = calls[calls.length - 1]![1] as {
    body: { content: { data_sources: ApiDataSource[] } }
  }
  return options.body.content.data_sources
}

test('toggling visibility in the appearance table drops the metric from the preview and back', async () => {
  renderBody('edit')
  await userEvent.click(await screen.findByRole('tab', { name: 'Graph appearance' }))
  const chart = screen.getByTestId('time-series-graph')
  await waitFor(() => expect(chart).toHaveTextContent('CPU'))

  const [hideA] = within(screen.getByRole('tabpanel')).getAllByRole('button', {
    name: 'Toggle visibility'
  })
  await fireEvent.click(hideA!)

  await waitFor(() => expect(chart).not.toHaveTextContent('CPU'))
  expect(chart).toHaveTextContent('Memory')

  await fireEvent.click(hideA!)
  await waitFor(() => expect(chart).toHaveTextContent('CPU'))
})

test.each([
  { kind: 'an RRD query', source: () => rrdQuerySource('Q'), metricBackendAvailable: false },
  {
    kind: 'a metrics backend query',
    source: () => ({ ...metricBackendItem('Q'), title: 'Q' }),
    metricBackendAvailable: true
  }
])(
  'hiding the parent of $kind takes every nested line off the preview at once',
  async ({ source, metricBackendAvailable }) => {
    vi.spyOn(client, 'POST').mockResolvedValue(
      fanOutResponse('Q', ['host-1', 'host-2', 'host-3']) as never
    )
    renderBody('edit', {
      graph: graphObject([source()]),
      metricBackendAvailable
    })
    await userEvent.click(await screen.findByRole('tab', { name: 'Graph appearance' }))
    await waitFor(() => expect(drawnTitles()).toBe('host-1,host-2,host-3'))

    // Nested lines carry no toggle of their own.
    const panel = screen.getByRole('tabpanel')
    const parentToggles = within(panel).getAllByRole('button', { name: 'Toggle visibility' })
    expect(parentToggles).toHaveLength(1)

    await fireEvent.click(parentToggles[0]!)

    await waitFor(() => expect(drawnTitles()).toBe(''))
  }
)

test('changing a line style sends the new representation with the next preview fetch', async () => {
  const postSpy = vi.spyOn(client, 'POST').mockResolvedValue(fetchDataResponse() as never)
  renderBody('edit', { graph: graphObject([rrdSource('A')]) })
  await userEvent.click(await screen.findByRole('tab', { name: 'Graph appearance' }))
  await waitFor(() => expect(postSpy).toHaveBeenCalled())
  expect(lastPostedSources(postSpy)[0]!.line_type).toBe('line')

  for (const { label, lineType } of [
    { label: 'Area', lineType: 'area' },
    { label: 'Stack', lineType: 'stack' }
  ]) {
    await fireEvent.click(screen.getByRole('combobox', { name: 'Line style' }))
    await fireEvent.click(await screen.findByRole('option', { name: label }))

    await waitFor(() => expect(lastPostedSources(postSpy)[0]!.line_type).toBe(lineType), {
      timeout: PAN_REFETCH_TIMEOUT_MS
    })
  }
})

test('a multi-selection query is one row to configure and one line per matching series', async () => {
  vi.spyOn(client, 'POST').mockResolvedValue(
    fanOutResponse('Q', ['host-1', 'host-2', 'host-3']) as never
  )
  renderBody('edit', { graph: graphObject([rrdQuerySource('Q')]) })
  await screen.findByRole('tab', { name: 'Metrics selection' })

  expect(within(screen.getByRole('tabpanel')).getAllByLabelText('Select row')).toHaveLength(1)

  await userEvent.click(screen.getByRole('tab', { name: 'Graph appearance' }))
  await waitFor(() => expect(drawnTitles()).toBe('host-1,host-2,host-3'))
})
