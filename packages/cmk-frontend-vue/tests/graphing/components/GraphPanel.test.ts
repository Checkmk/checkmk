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
import type { BurgerMenuCallable, RequestedTimeRange } from '@/graphing/types'

vi.mock('@/graphing/api/burgerMenu.ts', () => ({ loadMenu: vi.fn() }))

// Mock renders received metric titles and view props as text so tests can assert on
// visibility filtering and the interaction loop. Click targets are spans (not buttons)
// to keep the "panel renders no button" assertions meaningful.
vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: {
    inheritAttrs: false,
    props: ['metrics', 'time_range', 'inspecting'],
    emits: ['zoom', 'pan', 'reset'],
    template: `<div data-testid="time-series-graph">
      <span>{{ metrics.map((m) => m.metadata.title).join(",") }}</span>
      <span data-testid="view-start">{{ time_range.start }}</span>
      <span data-testid="inspecting">{{ inspecting }}</span>
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

beforeEach(() => {
  vi.mocked(loadMenu).mockResolvedValue([])
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
      addType: 'test',
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
      addType: 'test',
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
