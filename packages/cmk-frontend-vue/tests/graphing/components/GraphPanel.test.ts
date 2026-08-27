/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import { loadMenu } from '@/graphing/api/burgerMenu.ts'
import GraphPanel from '@/graphing/components/GraphPanel.vue'
import type { Metric, TimeRange } from '@/graphing/components/TimeSeriesGraph'
import { useGlobalPin } from '@/graphing/composables/useGlobalPin'
import type { BurgerMenuCallable, GraphPanelProps, RequestedTimeRange } from '@/graphing/types'

vi.mock('@/graphing/api/burgerMenu.ts', () => ({ loadMenu: vi.fn() }))

// Mock renders received metric titles and view props as text so tests can assert on
// visibility filtering and the interaction loop. Click targets are spans (not buttons)
// to keep the "panel renders no button" assertions meaningful.
vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: {
    inheritAttrs: false,
    props: [
      'metrics',
      'view_time_range',
      'inspecting',
      'highlightedMetricName',
      'pinEnabled',
      'pinTime',
      'atMinTimeZoom',
      'consolidationFunction',
      'options'
    ],
    emits: ['zoom', 'pan', 'reset', 'pinCreate', 'pinAction'],
    template: `<div data-testid="time-series-graph">
      <span>{{ metrics.map((m) => m.metadata.title).join(",") }}</span>
      <span data-testid="renderer-y-axis-range">{{ options?.y_axis?.explicit_range?.max ?? 'none' }}</span>
      <span data-testid="renderer-y-axis-unit">{{ options?.y_axis?.unit?.notation ?? 'none' }}</span>
      <span data-testid="view-start">{{ view_time_range.start }}</span>
      <span data-testid="view-end">{{ view_time_range.end }}</span>
      <span data-testid="inspecting">{{ inspecting }}</span>
      <span data-testid="highlighted">{{ highlightedMetricName }}</span>
      <span data-testid="show-pin">{{ pinEnabled }}</span>
      <span data-testid="pin-time">{{ pinTime }}</span>
      <span data-testid="at-min-time-zoom">{{ atMinTimeZoom }}</span>
      <span data-testid="renderer-consolidation">{{ consolidationFunction }}</span>
      <span data-testid="emit-pin-create" @click="$emit('pinCreate', { time: 1234 })" />
      <span data-testid="emit-pin-action" @click="$emit('pinAction', { time: 1234 })" />
      <span
        data-testid="emit-time-zoom"
        @click="$emit('zoom', { timeRange: { start: 100, end: 200, step: 10 } })"
      />
      <span
        data-testid="emit-value-zoom"
        @click="$emit('zoom', { timeRange: view_time_range, valueRange: { min: 0, max: 10 } })"
      />
      <span
        data-testid="emit-pan"
        @click="$emit('pan', { timeRange: { start: 300, end: 400, step: 10 } })"
      />
      <span
        data-testid="emit-pan-wide"
        @click="$emit('pan', { timeRange: { start: 342, end: 4002, step: 10 } })"
      />
      <span data-testid="emit-reset" @click="$emit('reset')" />
    </div>`
  }
}))

vi.mock('@/graphing/components/GraphBrush/GraphBrush.vue', () => ({
  default: {
    inheritAttrs: false,
    props: [
      'metrics',
      'domain',
      'dataDomain',
      'window',
      'minSpan',
      'width',
      'plotLeft',
      'plotWidth'
    ],
    emits: ['update:requestedTimeRange'],
    template: `<div class="graphing-graph-brush">
      <span data-testid="brush-window">{{ window.start }}-{{ window.end }}</span>
      <span data-testid="brush-domain">{{ domain.start }}-{{ domain.end }}</span>
      <span
        data-testid="emit-brush-move"
        @click="$emit('update:requestedTimeRange', { start: 300, end: 400 }, 'translated_timerange')"
      />
      <span
        data-testid="emit-brush-resize"
        @click="$emit('update:requestedTimeRange', { start: 320, end: 380 }, 'changed_timerange_span')"
      />
    </div>`
  }
}))

// The panel always arms the pin, so it is stubbed to keep these tests off the network.
vi.mock('@/graphing/composables/useGlobalPin', async () => {
  const { computed, ref } = await import('vue')
  const pinTimeState = ref<number | null>(null)
  const globalPin = {
    pinTime: computed(() => pinTimeState.value),
    ensurePinLoaded: vi.fn(),
    setPin: vi.fn((time: number) => {
      pinTimeState.value = time
    }),
    clearPin: vi.fn(() => {
      pinTimeState.value = null
    })
  }
  return { useGlobalPin: () => globalPin }
})

const UNIT: components['schemas']['ApiUnitFormat'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

const TIME_RANGE: TimeRange = { start: 1_781_524_800, end: 1_781_528_400, step: 300 }
const REQUESTED: RequestedTimeRange = { start: 1_781_524_800, end: 1_781_528_400 }
const FIGURE_WIDTH = 800

// All-disabled default keeps the "panel renders no button" assertions meaningful (zoom/pan
// controls and the burger all contribute buttons); tests opt into single capabilities.
const INTERACTION_NONE: GraphPanelProps['interaction'] = {
  burger: 'disabled',
  zoom: 'disabled',
  panning: 'disabled',
  hover: 'disabled',
  brush: 'disabled',
  pin: 'disabled'
}

function makeMetric(name: string, title: string): Metric {
  return {
    metadata: { name, title, unit: UNIT, color: '#ff0000' },
    render: { stack: 'area', inverse: false, hidden: false },
    data_points: [1, 2, 3]
  }
}

const CPU = makeMetric('cpu', 'CPU')
const MEM = makeMetric('mem', 'Memory')

const BRUSH_SNAPSHOT: GraphPanelProps['brushSnapshot'] = {
  drawnDomain: { start: TIME_RANGE.start - 3 * 3_600, end: TIME_RANGE.end },
  window: { start: TIME_RANGE.start, end: TIME_RANGE.end },
  data: { metrics: [CPU], dataTimeRange: TIME_RANGE }
}

function renderPanelWithLegend(metrics: Metric[], hiddenMetricNames: string[] = []) {
  return render(GraphPanel, {
    props: {
      metrics,
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      hiddenMetricNames,
      showLegend: true
    }
  })
}

/** The legend's visibility toggle for a metric; it is labelled with the metric's title. */
function eyeButtonFor(metricTitle: string): HTMLElement {
  return screen.getByRole('button', { name: metricTitle })
}

/** The legend row for a metric; hovering it is what emits the highlight. */
function legendRowFor(metricTitle: string): HTMLElement {
  return screen.getByRole('row', { name: new RegExp(metricTitle) })
}

/** The element carrying the plot's interaction state, which the renderer is mounted into. */
function plotWrapper(): HTMLElement {
  return screen.getByTestId('time-series-graph').parentElement!
}

// The mocked pin is a module-level singleton, so it has to be cleared between tests.
beforeEach(() => {
  vi.mocked(loadMenu).mockResolvedValue([])
  useGlobalPin().clearPin()
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

const MID_INTERVAL_REQUEST: RequestedTimeRange = { start: 1_781_524_937, end: 1_781_528_237 }
const GRID_BOUNDARY_AT_OR_BEFORE_REQUEST_START = 1_781_524_800
const NEWEST_GRID_BOUNDARY_THE_REQUEST_COVERS = 1_781_528_100
const RESOLUTION_OF_THE_SERVED_STEP = /5 min/
const ANY_RESOLUTION = /min/

function renderPanelForRequest(overrides: Partial<GraphPanelProps> = {}) {
  return render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: MID_INTERVAL_REQUEST,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      ...overrides
    }
  })
}

test('starts the drawn window on the sample boundary at or before the one requested', () => {
  renderPanelForRequest()

  expect(screen.getByTestId('view-start')).toHaveTextContent(
    String(GRID_BOUNDARY_AT_OR_BEFORE_REQUEST_START)
  )
})

test('ends the drawn window on the newest sample boundary the request covers', () => {
  renderPanelForRequest()

  expect(screen.getByTestId('view-end')).toHaveTextContent(
    String(NEWEST_GRID_BOUNDARY_THE_REQUEST_COVERS)
  )
})

test('states the resolution the fetch resolved once one has landed', async () => {
  renderPanelForRequest({ showTimestamp: true })

  expect(await screen.findByText(RESOLUTION_OF_THE_SERVED_STEP)).toBeInTheDocument()
})

test('states no resolution until a fetch has resolved one', () => {
  renderPanelForRequest({ showTimestamp: true, dataTimeRange: undefined })

  expect(screen.queryByText(ANY_RESOLUTION)).not.toBeInTheDocument()
})

test('does not render the legend when showLegend is not set', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })
  expect(document.querySelector('.graphing-graph-panel__legend')).not.toBeInTheDocument()
})

test('renders the legend when showLegend is true', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      showLegend: true
    }
  })
  expect(document.querySelector('.graphing-graph-panel__legend')).toBeInTheDocument()
})

test('the brush bar shows the committed window, not the range the curves are drawn against', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      // A range from some earlier fetch, which is what the panel draws while awaiting data.
      dataTimeRange: { start: 1, end: 2, step: 300 },
      awaitingData: true,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: { ...INTERACTION_NONE, brush: 'enabled' },
      brushSnapshot: BRUSH_SNAPSHOT
    }
  })

  const { window } = BRUSH_SNAPSHOT!
  expect(screen.getByTestId('brush-window')).toHaveTextContent(`${window.start}-${window.end}`)
})

test('renders the context view when showBrush is set and a brush snapshot is supplied', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: { ...INTERACTION_NONE, brush: 'enabled' },
      brushSnapshot: BRUSH_SNAPSHOT
    }
  })
  expect(document.querySelector('.graphing-graph-brush')).toBeInTheDocument()
})

function renderPanelWithBrush() {
  return render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      // Same span as the brush move below, so the published range is the moved one.
      requestedTimeRange: { start: 200, end: 300 },
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: { ...INTERACTION_NONE, brush: 'enabled' },
      brushSnapshot: BRUSH_SNAPSHOT
    }
  })
}

test.each([
  ['emit-brush-move', { start: 300, end: 400 }, 'translated_timerange'],
  ['emit-brush-resize', { start: 320, end: 380 }, 'changed_timerange_span']
] as const)(
  'a brush %s publishes the requested time range it reported',
  async (testId, range, kind) => {
    const { emitted } = renderPanelWithBrush()

    await fireEvent.click(screen.getByTestId(testId))

    expect(emitted()['update:requestedTimeRange']).toEqual([[range, kind]])
  }
)

test('a brush change activates inspection, so the reset affordance is offered', async () => {
  renderPanelWithBrush()
  expect(screen.getByTestId('inspecting')).toHaveTextContent('false')

  await fireEvent.click(screen.getByTestId('emit-brush-move'))

  expect(screen.getByTestId('inspecting')).toHaveTextContent('true')
})

test('a peak zoom outlives a time range the host requested without a new-window count', async () => {
  const { rerender } = renderPanelWithBrush()
  await fireEvent.click(screen.getByTestId('emit-value-zoom'))

  await rerender({ requestedTimeRange: { start: 5_000, end: 6_000 } })

  expect(screen.getByTestId('inspecting')).toHaveTextContent('true')
})

test('a peak zoom ends when a time control asks for another window', async () => {
  const { rerender } = renderPanelWithBrush()
  await fireEvent.click(screen.getByTestId('emit-value-zoom'))

  await rerender({ requestedTimeRange: { start: 5_000, end: 6_000 }, timePickerRequests: 1 })

  expect(screen.getByTestId('inspecting')).toHaveTextContent('false')
})

test('a peak zoom ends on a new-window count even when the range is unchanged', async () => {
  const { rerender } = renderPanelWithBrush()
  await fireEvent.click(screen.getByTestId('emit-value-zoom'))

  await rerender({ timePickerRequests: 1 })

  expect(screen.getByTestId('inspecting')).toHaveTextContent('false')
})

test('does not render the context view when showBrush is not set', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      brushSnapshot: BRUSH_SNAPSHOT
    }
  })
  expect(document.querySelector('.graphing-graph-brush')).not.toBeInTheDocument()
})

// The renderer refuses a zoom drag on this flag, and it has to be read off the requested
// window: the served window is snapped to the data step, so it stays wider than the floor even
// at maximum zoom and would leave the limit unreachable.
test('reports time zoom at its floor once the requested window is the narrowest servable one', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      interaction: INTERACTION_NONE,
      // A minute apart: exactly MIN_ZOOM_TIME_RANGE_SECONDS.
      requestedTimeRange: { start: 1_781_524_800, end: 1_781_524_860 },
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      // Served a step wider, as the backend does.
      dataTimeRange: { start: 1_781_524_800, end: 1_781_524_920, step: 60 }
    }
  })

  expect(screen.getByTestId('at-min-time-zoom')).toHaveTextContent('true')
})

test('does not report time zoom at its floor while the requested window is still wider', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      interaction: INTERACTION_NONE,
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH
    }
  })

  expect(screen.getByTestId('at-min-time-zoom')).toHaveTextContent('false')
})

test('does not render GraphBurgerMenu when showBurgerMenu is not set', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })
  expect(screen.queryByRole('button', { name: 'Action menu' })).not.toBeInTheDocument()
})

test('does not render GraphBurgerMenu when the burger interaction is disabled', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      addTo: { type: 'test', specification: {}, internal: '{"graphs":[]}' },
      interaction: INTERACTION_NONE
    }
  })
  expect(screen.queryByRole('button', { name: 'Action menu' })).not.toBeInTheDocument()
})

test('renders GraphBurgerMenu when the burger interaction is enabled, and is accessible by role="button" and its "Action menu" aria label', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      addTo: { type: 'test', specification: {}, internal: '{"graphs":[]}' },
      interaction: { ...INTERACTION_NONE, burger: 'enabled' }
    }
  })
  expect(screen.getByRole('button', { name: 'Action menu' })).toBeInTheDocument()
})

test('a do-action from the header runs the callback with the graph the backends address', async () => {
  const onClick: BurgerMenuCallable = vi.fn()
  vi.mocked(loadMenu).mockResolvedValue([
    {
      heading: 'Export',
      actions: [{ label: 'Export as JSON', ariaLabel: 'Export as JSON', onClick }]
    }
  ])
  const specification = { graph_type: 'template', graph_id: 'cpu_load' }
  const internal = '{"graphs":[{"kind":"template"}]}'

  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      addTo: { type: 'test', specification, internal },
      interaction: { ...INTERACTION_NONE, burger: 'enabled' }
    }
  })

  await fireEvent.click(screen.getByRole('button', { name: 'Action menu' }))
  await fireEvent.click(await screen.findByRole('button', { name: 'Export as JSON' }))

  // Most add-to actions replay the specification, a custom graph takes the built graph itself, and
  // the export additionally needs the shown range.
  expect(onClick).toHaveBeenCalledWith({
    specification,
    internal,
    timeStart: REQUESTED.start,
    timeEnd: REQUESTED.end,
    consolidationFunction: 'max'
  })
})

async function selectConsolidationFromHeaderDropdown(label: string): Promise<void> {
  const user = userEvent.setup()
  await user.click(screen.getByRole('combobox', { name: 'Graph values' }))
  await user.click(await screen.findByRole('option', { name: label }))
}

function rendererConsolidation(): HTMLElement {
  return screen.getByTestId('renderer-consolidation')
}

function renderPanelWithConsolidation() {
  return render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      showConsolidation: true
    }
  })
}

test('consolidates with max until the header selects otherwise', () => {
  renderPanelWithConsolidation()
  expect(rendererConsolidation()).toHaveTextContent('max')
})

test('reports the header selection to the host and hands it to the renderer', async () => {
  const { emitted } = renderPanelWithConsolidation()

  await selectConsolidationFromHeaderDropdown('Min')

  expect(emitted()['update:consolidationFn']).toEqual([['min']])
  expect(rendererConsolidation()).toHaveTextContent('min')
})

test('the burger menu addresses the graph with the selected consolidation function', async () => {
  const onClick: BurgerMenuCallable = vi.fn()
  vi.mocked(loadMenu).mockResolvedValue([
    { heading: 'Export', actions: [{ label: 'Export', ariaLabel: 'Export', onClick }] }
  ])
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      addTo: { type: 'test', specification: {}, internal: '{"graphs":[]}' },
      interaction: { ...INTERACTION_NONE, burger: 'enabled' },
      showConsolidation: true
    }
  })

  await selectConsolidationFromHeaderDropdown('Average')
  await fireEvent.click(screen.getByRole('button', { name: 'Action menu' }))
  await fireEvent.click(await screen.findByRole('button', { name: 'Export' }))

  expect(onClick).toHaveBeenCalledWith(expect.objectContaining({ consolidationFunction: 'avg' }))
})

test('renders title when showTitle is true', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      title: 'Panel Title',
      showTitle: true
    }
  })
  expect(screen.getByText('Panel Title')).toBeInTheDocument()
})

test('applies legend-right modifier class when legendPosition is "right"', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      legendPosition: 'right'
    }
  })
  expect(
    document.querySelector('.graphing-graph-panel__container--legend-right')
  ).toBeInTheDocument()
})

test('does not apply legend-right modifier class when legendPosition is "bottom"', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      legendPosition: 'bottom'
    }
  })
  expect(
    document.querySelector('.graphing-graph-panel__container--legend-right')
  ).not.toBeInTheDocument()
})

test('the renderer receives the baseline view without inspection', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  expect(screen.getByTestId('view-start')).toHaveTextContent(String(TIME_RANGE.start))
  expect(screen.getByTestId('inspecting')).toHaveTextContent('false')
})

test('a zoom intent from the renderer overlays the view and activates inspection', async () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  await fireEvent.click(screen.getByTestId('emit-time-zoom'))

  expect(screen.getByTestId('view-start')).toHaveTextContent('100')
  expect(screen.getByTestId('inspecting')).toHaveTextContent('true')
})

test('a zoom intent from the renderer also publishes a requested time range update', async () => {
  const { emitted } = render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  await fireEvent.click(screen.getByTestId('emit-time-zoom'))

  expect(emitted()['update:requestedTimeRange']).toEqual([
    [{ start: 100, end: 200 }, 'changed_timerange_span']
  ])
})

test('a value-zoom intent from the renderer does not publish a requested time range update', async () => {
  const { emitted } = render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  await fireEvent.click(screen.getByTestId('emit-value-zoom'))

  expect(emitted()['update:requestedTimeRange']).toBeUndefined()
})

test('a pan intent from the renderer also publishes a requested time range update', async () => {
  const { emitted } = render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      // Same span as the pan below, so the published range is the panned one.
      requestedTimeRange: { start: 200, end: 300 },
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  await fireEvent.click(screen.getByTestId('emit-pan'))

  expect(emitted()['update:requestedTimeRange']).toEqual([
    [{ start: 300, end: 400 }, 'translated_timerange']
  ])
})

test('a pan asks for the span that was requested, not the wider one that was served', async () => {
  const { emitted } = render(GraphPanel, {
    props: {
      metrics: [CPU],
      // Served a step wider than requested, as the backend does.
      dataTimeRange: { start: 1_781_524_800, end: 1_781_528_460, step: 60 },
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  // The renderer pans the served window, so it hands over the wider span.
  await fireEvent.click(screen.getByTestId('emit-pan-wide'))

  expect(emitted()['update:requestedTimeRange']).toEqual([
    [{ start: 342, end: 3_942 }, 'translated_timerange']
  ])
})

describe('reporting inspection to the host', () => {
  test.each([
    ['a value-zoom', 'emit-value-zoom'],
    ['a time-zoom', 'emit-time-zoom'],
    ['a pan', 'emit-pan']
  ])('%s intent from the renderer reports inspection', async (_gesture, emitTestId) => {
    const { emitted } = render(GraphPanel, {
      props: {
        metrics: [CPU],
        dataTimeRange: TIME_RANGE,
        requestedTimeRange: REQUESTED,
        timePickerRequests: 0,
        figureWidth: FIGURE_WIDTH,
        interaction: INTERACTION_NONE
      }
    })

    await fireEvent.click(screen.getByTestId(emitTestId))

    expect(emitted()['inspect']).toHaveLength(1)
  })

  test.each([
    ['a brush move', 'emit-brush-move'],
    ['a brush resize', 'emit-brush-resize']
  ])('%s reports inspection', async (_gesture, emitTestId) => {
    const { emitted } = renderPanelWithBrush()

    await fireEvent.click(screen.getByTestId(emitTestId))

    expect(emitted()['inspect']).toHaveLength(1)
  })

  test('a reset intent does not report inspection', async () => {
    const { emitted } = render(GraphPanel, {
      props: {
        metrics: [CPU],
        dataTimeRange: TIME_RANGE,
        requestedTimeRange: REQUESTED,
        timePickerRequests: 0,
        figureWidth: FIGURE_WIDTH,
        interaction: INTERACTION_NONE
      }
    })

    await fireEvent.click(screen.getByTestId('emit-reset'))

    expect(emitted()['inspect']).toBeUndefined()
  })
})

test('a reset intent from the renderer also publishes a requested time range update', async () => {
  const { emitted } = render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })
  await fireEvent.click(screen.getByTestId('emit-time-zoom'))

  await fireEvent.click(screen.getByTestId('emit-reset'))

  expect(emitted()['update:requestedTimeRange']).toEqual([
    [{ start: 100, end: 200 }, 'changed_timerange_span'],
    [{ start: TIME_RANGE.start, end: TIME_RANGE.end }, 'changed_timerange_span']
  ])
})

test('a reset intent from the renderer restores the baseline view', async () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })
  await fireEvent.click(screen.getByTestId('emit-time-zoom'))

  await fireEvent.click(screen.getByTestId('emit-reset'))

  expect(screen.getByTestId('view-start')).toHaveTextContent(String(TIME_RANGE.start))
  expect(screen.getByTestId('inspecting')).toHaveTextContent('false')
})

test('the renderer receives every metric when none are hidden', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  expect(screen.getByTestId('time-series-graph')).toHaveTextContent('CPU,Memory')
})

test('hiding a metric via the legend eye removes it from what TimeSeriesGraph receives', async () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      showLegend: true
    }
  })
  const cpuRow = screen.getByText('CPU').closest('tr')!

  await fireEvent.click(cpuRow.querySelector('button')!)

  expect(screen.getByTestId('time-series-graph')).toHaveTextContent('Memory')
  expect(screen.getByTestId('time-series-graph')).not.toHaveTextContent('CPU')
})

test('a metric hidden via the hiddenMetricNames model is filtered from the renderer', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      hiddenMetricNames: ['cpu'],
      interaction: INTERACTION_NONE
    }
  })

  expect(screen.getByTestId('time-series-graph')).toHaveTextContent('Memory')
  expect(screen.getByTestId('time-series-graph')).not.toHaveTextContent('CPU')
})

test('toggling a metric requests no new data', async () => {
  const { emitted } = render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      showLegend: true
    }
  })
  await fireEvent.click(eyeButtonFor('CPU'))

  expect(emitted()['update:requestedTimeRange']).toBeUndefined()
})

test('un-hiding a metric restores it to the renderer, and so to the tooltip', async () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      hiddenMetricNames: ['cpu'],
      showLegend: true
    }
  })
  await fireEvent.click(eyeButtonFor('CPU'))

  expect(screen.getByTestId('time-series-graph')).toHaveTextContent('CPU,Memory')
})

test('toggling two of five metrics hides exactly those two', async () => {
  const metrics = [
    makeMetric('cpu', 'CPU'),
    makeMetric('mem', 'Memory'),
    makeMetric('disk', 'Disk'),
    makeMetric('net', 'Network'),
    makeMetric('swap', 'Swap')
  ]
  render(GraphPanel, {
    props: {
      metrics,
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      showLegend: true
    }
  })

  await fireEvent.click(eyeButtonFor('CPU'))
  await fireEvent.click(eyeButtonFor('Network'))

  expect(screen.getByTestId('time-series-graph')).toHaveTextContent('Memory,Disk,Swap')
})

test('hovering a legend row propagates the highlight to the renderer', async () => {
  renderPanelWithLegend([CPU, MEM])
  const cpuRow = legendRowFor('CPU')

  await fireEvent.mouseEnter(cpuRow)

  expect(screen.getByTestId('highlighted')).toHaveTextContent('cpu')
})

test('leaving a legend row clears the highlight again', async () => {
  renderPanelWithLegend([CPU, MEM])
  const cpuRow = legendRowFor('CPU')
  await fireEvent.mouseEnter(cpuRow)

  await fireEvent.mouseLeave(cpuRow)

  expect(screen.getByTestId('highlighted')).toBeEmptyDOMElement()
})

test('hiding every metric keeps the frame and states why', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      hiddenMetricNames: ['cpu', 'mem'],
      showLegend: true
    }
  })

  expect(screen.getByText('All metrics are hidden')).toBeInTheDocument()
  expect(screen.getByTestId('time-series-graph')).toBeInTheDocument()
  expect(plotWrapper()).toHaveClass('graphing-graph-panel__plot--inert')
})

test('bringing one metric back clears the empty state', async () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      hiddenMetricNames: ['cpu', 'mem'],
      showLegend: true
    }
  })

  await fireEvent.click(eyeButtonFor('CPU'))

  expect(screen.queryByText('All metrics are hidden')).not.toBeInTheDocument()
  expect(screen.getByTestId('time-series-graph')).toHaveTextContent('CPU')
  expect(plotWrapper()).not.toHaveClass('graphing-graph-panel__plot--inert')
})

// Without this the persisted pin is loaded but never drawn.
test('the renderer is told to offer the pin affordance', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: { ...INTERACTION_NONE, pin: 'enabled' }
    }
  })

  expect(screen.getByTestId('show-pin')).toHaveTextContent('true')
})

test('a pin intent from the renderer stores the pinned time', async () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  await fireEvent.click(screen.getByTestId('emit-pin-create'))

  expect(screen.getByTestId('pin-time')).toHaveTextContent('1234')
})

test('acting on an existing pin removes it', async () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })
  await fireEvent.click(screen.getByTestId('emit-pin-create'))

  await fireEvent.click(screen.getByTestId('emit-pin-action'))

  expect(screen.getByTestId('pin-time')).toBeEmptyDOMElement()
})

test('draws its frame from the requested range before any data has arrived', () => {
  // A distinct window from REQUESTED/TIME_RANGE, which share a start, so the assertion can tell
  // which range the frame was built from.
  render(GraphPanel, {
    props: {
      metrics: [],
      requestedTimeRange: { start: 1_700_000_000, end: 1_700_003_600 },
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  expect(screen.getByTestId('time-series-graph')).toBeInTheDocument()
  expect(screen.getByTestId('view-start')).toHaveTextContent('1700000000')
})

test('keeps the all-hidden message when data arrived but nothing is shown', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      hiddenMetricNames: ['cpu']
    }
  })

  // The empty frame must not swallow this case: hidden metrics are not the same as none.
  expect(screen.getByText('All metrics are hidden')).toBeInTheDocument()
  expect(screen.getByTestId('time-series-graph')).toBeInTheDocument()
})

test('a window that returned no data reuses the all-hidden message', () => {
  render(GraphPanel, {
    props: {
      metrics: [],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE
    }
  })

  // Pins today's wording: nothing was hidden, there was nothing to show. Change both together.
  expect(screen.getByText('All metrics are hidden')).toBeInTheDocument()
  expect(screen.getByTestId('time-series-graph')).toBeInTheDocument()
})

test('forwards a provided y-axis, explicit range included, into the renderer options', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      yAxis: { unit: UNIT, explicit_range: { min: 1, max: 5 } }
    }
  })

  expect(screen.getByTestId('renderer-y-axis-range')).toHaveTextContent('5')
})

test('derives the renderer y-axis from the metrics when none is provided', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      timePickerRequests: 0,
      figureWidth: FIGURE_WIDTH,
      interaction: INTERACTION_NONE,
      yAxis: null
    }
  })

  // The unit comes from the metric, and no explicit range is invented.
  expect(screen.getByTestId('renderer-y-axis-unit')).toHaveTextContent('decimal')
  expect(screen.getByTestId('renderer-y-axis-range')).toHaveTextContent('none')
})
