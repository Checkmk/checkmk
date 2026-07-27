/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import { loadMenu } from '@/graphing/api/burgerMenu.ts'
import GraphPanel from '@/graphing/components/GraphPanel.vue'
import type { Metric, TimeRange } from '@/graphing/components/TimeSeriesGraph'
import { useGlobalPin } from '@/graphing/composables/useGlobalPin'
import type { BurgerMenuCallable, RequestedTimeRange } from '@/graphing/types'

vi.mock('@/graphing/api/burgerMenu.ts', () => ({ loadMenu: vi.fn() }))

// Mock renders received metric titles and view props as text so tests can assert on
// visibility filtering and the interaction loop. Click targets are spans (not buttons)
// to keep the "panel renders no button" assertions meaningful.
vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: {
    inheritAttrs: false,
    props: ['metrics', 'time_range', 'inspecting', 'highlightedMetricName', 'showPin', 'pinTime'],
    emits: ['zoom', 'pan', 'reset', 'pinCreate', 'pinAction'],
    template: `<div data-testid="time-series-graph">
      <span>{{ metrics.map((m) => m.metadata.title).join(",") }}</span>
      <span data-testid="view-start">{{ time_range.start }}</span>
      <span data-testid="inspecting">{{ inspecting }}</span>
      <span data-testid="highlighted">{{ highlightedMetricName }}</span>
      <span data-testid="show-pin">{{ showPin }}</span>
      <span data-testid="pin-time">{{ pinTime }}</span>
      <span data-testid="emit-pin-create" @click="$emit('pinCreate', { time: 1234 })" />
      <span data-testid="emit-pin-action" @click="$emit('pinAction', { time: 1234 })" />
      <span
        data-testid="emit-time-zoom"
        @click="$emit('zoom', { timeRange: { start: 100, end: 200, step: 10 } })"
      />
      <span
        data-testid="emit-value-zoom"
        @click="$emit('zoom', { timeRange: time_range, valueRange: { min: 0, max: 10 } })"
      />
      <span
        data-testid="emit-pan"
        @click="$emit('pan', { timeRange: { start: 300, end: 400, step: 10 } })"
      />
      <span data-testid="emit-reset" @click="$emit('reset')" />
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

function makeMetric(name: string, title: string): Metric {
  return {
    metadata: { name, title, unit: UNIT, color: '#ff0000' },
    render: { stack: 'area', inverse: false, hidden: false },
    data_points: [1, 2, 3]
  }
}

const CPU = makeMetric('cpu', 'CPU')
const MEM = makeMetric('mem', 'Memory')

function renderPanelWithLegend(metrics: Metric[], hiddenMetricNames: string[] = []) {
  return render(GraphPanel, {
    props: {
      metrics,
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
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

// The mocked pin is a module-level singleton, so it has to be cleared between tests.
beforeEach(() => {
  vi.mocked(loadMenu).mockResolvedValue([])
  useGlobalPin().clearPin()
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

test('does not render the legend when showLegend is not set', () => {
  render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })
  expect(document.querySelector('.graphing-graph-panel__legend')).not.toBeInTheDocument()
})

test('renders the legend when showLegend is true', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      showLegend: true
    }
  })
  expect(document.querySelector('.graphing-graph-panel__legend')).toBeInTheDocument()
})

test('renders the context view when showBrush is set and an overview is supplied', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      showBrush: true,
      overview: { metrics: [CPU], timeRange: TIME_RANGE }
    }
  })
  expect(document.querySelector('.graphing-graph-brush')).toBeInTheDocument()
})

test('does not render the context view when showBrush is not set', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      overview: { metrics: [CPU], timeRange: TIME_RANGE }
    }
  })
  expect(document.querySelector('.graphing-graph-brush')).not.toBeInTheDocument()
})

test('does not render GraphBurgerMenu when showBurgerMenu is not set', () => {
  render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})

test('renders GraphBurgerMenu when showBurgerMenu is true', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      addTo: { type: 'test', specification: {} },
      internal: 'test'
    }
  })
  expect(screen.getByRole('button')).toBeInTheDocument()
})

test('a do-action from the header runs the callback with the panel internal state', async () => {
  const onClick: BurgerMenuCallable = vi.fn()
  vi.mocked(loadMenu).mockResolvedValue([
    {
      heading: 'Export',
      actions: [{ label: 'Export as JSON', ariaLabel: 'Export as JSON', onClick }]
    }
  ])

  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      addTo: { type: 'test', specification: {} },
      internal: 'panel-internal-state'
    }
  })

  await fireEvent.click(screen.getByRole('button'))
  await fireEvent.click(await screen.findByRole('button', { name: 'Export as JSON' }))

  expect(onClick).toHaveBeenCalledWith('panel-internal-state')
})

test('renders title when showTitle is true', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
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
      legendPosition: 'bottom'
    }
  })
  expect(
    document.querySelector('.graphing-graph-panel__container--legend-right')
  ).not.toBeInTheDocument()
})

test('the renderer receives the baseline view without inspection', () => {
  render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })

  expect(screen.getByTestId('view-start')).toHaveTextContent(String(TIME_RANGE.start))
  expect(screen.getByTestId('inspecting')).toHaveTextContent('false')
})

test('a zoom intent from the renderer overlays the view and activates inspection', async () => {
  render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })

  await fireEvent.click(screen.getByTestId('emit-time-zoom'))

  expect(screen.getByTestId('view-start')).toHaveTextContent('100')
  expect(screen.getByTestId('inspecting')).toHaveTextContent('true')
})

test('a zoom intent from the renderer also publishes a requested time range update', async () => {
  const { emitted } = render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })

  await fireEvent.click(screen.getByTestId('emit-time-zoom'))

  expect(emitted()['update:requestedTimeRange']).toEqual([
    [{ start: 100, end: 200 }, 'changed_timerange_span']
  ])
})

test('a value-zoom intent from the renderer does not publish a requested time range update', async () => {
  const { emitted } = render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })

  await fireEvent.click(screen.getByTestId('emit-value-zoom'))

  expect(emitted()['update:requestedTimeRange']).toBeUndefined()
})

test('a pan intent from the renderer also publishes a requested time range update', async () => {
  const { emitted } = render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })

  await fireEvent.click(screen.getByTestId('emit-pan'))

  expect(emitted()['update:requestedTimeRange']).toEqual([
    [{ start: 300, end: 400 }, 'translated_timerange']
  ])
})

test('a reset intent from the renderer also publishes a requested time range update', async () => {
  const { emitted } = render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
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
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })
  await fireEvent.click(screen.getByTestId('emit-time-zoom'))

  await fireEvent.click(screen.getByTestId('emit-reset'))

  expect(screen.getByTestId('view-start')).toHaveTextContent(String(TIME_RANGE.start))
  expect(screen.getByTestId('inspecting')).toHaveTextContent('false')
})

test('the renderer receives every metric when none are hidden', () => {
  render(GraphPanel, {
    props: { metrics: [CPU, MEM], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })

  expect(screen.getByTestId('time-series-graph')).toHaveTextContent('CPU,Memory')
})

test('hiding a metric via the legend eye removes it from what TimeSeriesGraph receives', async () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
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
      hiddenMetricNames: ['cpu']
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

test('hiding every metric replaces the graph with an empty state', () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      hiddenMetricNames: ['cpu', 'mem'],
      showLegend: true
    }
  })

  expect(screen.getByText('All metrics are hidden')).toBeInTheDocument()
  expect(screen.queryByTestId('time-series-graph')).not.toBeInTheDocument()
})

test('bringing one metric back clears the empty state', async () => {
  render(GraphPanel, {
    props: {
      metrics: [CPU, MEM],
      dataTimeRange: TIME_RANGE,
      requestedTimeRange: REQUESTED,
      hiddenMetricNames: ['cpu', 'mem'],
      showLegend: true
    }
  })

  await fireEvent.click(eyeButtonFor('CPU'))

  expect(screen.queryByText('All metrics are hidden')).not.toBeInTheDocument()
  expect(screen.getByTestId('time-series-graph')).toHaveTextContent('CPU')
})

// Without this the persisted pin is loaded but never drawn.
test('the renderer is told to offer the pin affordance', () => {
  render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })

  expect(screen.getByTestId('show-pin')).toHaveTextContent('true')
})

test('a pin intent from the renderer stores the pinned time', async () => {
  render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })

  await fireEvent.click(screen.getByTestId('emit-pin-create'))

  expect(screen.getByTestId('pin-time')).toHaveTextContent('1234')
})

test('acting on an existing pin removes it', async () => {
  render(GraphPanel, {
    props: { metrics: [CPU], dataTimeRange: TIME_RANGE, requestedTimeRange: REQUESTED }
  })
  await fireEvent.click(screen.getByTestId('emit-pin-create'))

  await fireEvent.click(screen.getByTestId('emit-pin-action'))

  expect(screen.getByTestId('pin-time')).toBeEmptyDOMElement()
})
