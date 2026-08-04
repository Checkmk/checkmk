/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { afterEach, vi } from 'vitest'
import { nextTick } from 'vue'

import type { HorizontalLine, Metric } from '@/graphing/components/TimeSeriesGraph'
import type { M4Bucket } from '@/graphing/components/TimeSeriesGraph/decimation/types'
import { computeStackedSeries } from '@/graphing/components/TimeSeriesGraph/render/stacked'
import GraphLegend from '@/graphing/components/legend/GraphLegend.vue'

// A single-sample bucket so every consolidation (min/max/avg) resolves to the same value,
// matching the fixture already used in TimeSeriesGraph/render/stacked.test.ts.
function makeBucket(value: number): M4Bucket {
  return {
    startTime: 0,
    endTime: 1,
    gap: false,
    minValue: value,
    maxValue: value,
    minValueTime: 0,
    maxValueTime: 0,
    firstValue: value,
    firstValueTime: 0,
    lastValue: value,
    lastValueTime: 0,
    sampleCount: 1,
    valueSum: value
  }
}

// jsdom has no ResizeObserver, so stub one that records its observe calls and lets tests
// trigger its callback directly to simulate a resize.
class FakeResizeObserver {
  static instances: FakeResizeObserver[] = []
  observed: Element[] = []
  constructor(public callback: ResizeObserverCallback) {
    FakeResizeObserver.instances.push(this)
  }
  observe(el: Element): void {
    this.observed.push(el)
  }
  unobserve(el: Element): void {
    this.observed = this.observed.filter((other) => other !== el)
  }
  disconnect(): void {
    this.observed = []
  }
}

afterEach(() => {
  FakeResizeObserver.instances = []
  vi.unstubAllGlobals()
})

const UNIT: Metric['metadata']['unit'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

function makeMetric(name: string, title: string, dataPoints: (number | null)[]): Metric {
  return {
    metadata: { name, title, unit: UNIT, color: '#ff0000' },
    render: { stack: 'area', inverse: false, hidden: false },
    data_points: dataPoints
  }
}

function makeMetricWithStack(name: string, title: string, stack: string | null): Metric {
  return {
    metadata: { name, title, unit: UNIT, color: '#ff0000' },
    render: { stack, inverse: false, hidden: false },
    data_points: [1]
  }
}

const CPU = makeMetric('cpu', 'CPU', [10, 20, 30])
const MEM = makeMetric('mem', 'Memory', [100, 200, 300])

test('renders one row per metric', () => {
  render(GraphLegend, { props: { metrics: [CPU, MEM] } })
  expect(screen.getByText('CPU')).toBeInTheDocument()
  expect(screen.getByText('Memory')).toBeInTheDocument()
})

test('with fewer than 10 metrics, count is shown as non-interactive text', () => {
  render(GraphLegend, { props: { metrics: [CPU] } })
  expect(screen.getByText(/1 metric/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /1 metric/ })).not.toBeInTheDocument()
})

test('with 10 or more metrics, count is a button that emits requestShowAll', async () => {
  const metrics = Array.from({ length: 10 }, (_, i) => makeMetric(`m${i}`, `Metric ${i}`, [i]))
  const { emitted } = render(GraphLegend, { props: { metrics } })
  await fireEvent.click(screen.getByRole('button', { name: /10 metrics/ }))
  expect(emitted()).toHaveProperty('requestShowAll')
})

test('clicking a visible metric eye emits update:hiddenMetricNames with that name added', async () => {
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU, MEM], hiddenMetricNames: [] }
  })
  const cpuRow = screen.getByText('CPU').closest('tr')!
  await fireEvent.click(cpuRow.querySelector('button')!)
  expect(emitted()['update:hiddenMetricNames']).toEqual([[['cpu']]])
})

test('clicking a hidden metric eye emits update:hiddenMetricNames with that name removed', async () => {
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU], hiddenMetricNames: ['cpu'] }
  })
  const cpuRow = screen.getByText('CPU').closest('tr')!
  await fireEvent.click(cpuRow.querySelector('button')!)
  expect(emitted()['update:hiddenMetricNames']).toEqual([[[]]])
})

test('hovering a metric row emits hoverMetric with the name, mouseleave emits null', async () => {
  const { emitted } = render(GraphLegend, { props: { metrics: [CPU] } })
  const row = screen.getByText('CPU').closest('tr')!
  await fireEvent.mouseEnter(row)
  await fireEvent.mouseLeave(row)
  expect(emitted()['hoverMetric']).toEqual([['cpu'], [null]])
})

// An entry that jumps position when clicked is impossible to re-find.
test('hiding a metric leaves the row order untouched', () => {
  const disk = makeMetric('disk', 'Disk', [1, 2, 3])

  const { container } = render(GraphLegend, {
    props: { metrics: [CPU, MEM, disk], hiddenMetricNames: ['mem'] }
  })

  const names = Array.from(container.querySelectorAll('.graphing-graph-legend__name')).map((el) =>
    el.textContent?.trim()
  )
  expect(names).toEqual(['Disk', 'Memory', 'CPU'])
})

test('a hidden metric keeps its entry, with its toggle showing it is off', () => {
  render(GraphLegend, { props: { metrics: [CPU, MEM], hiddenMetricNames: ['cpu'] } })

  expect(screen.getByRole('button', { name: 'CPU' })).toHaveAttribute('aria-pressed', 'false')
  expect(screen.getByRole('button', { name: 'Memory' })).toHaveAttribute('aria-pressed', 'true')
})

test('horizontal lines render with their title and value', () => {
  const line: HorizontalLine = {
    name: 'scalar_of(warning,rrd_metric(h/svc/util))',
    title: 'Warning',
    value: 80,
    color: '#ffaa00'
  }
  render(GraphLegend, { props: { metrics: [CPU], horizontalLines: [line] } })
  expect(screen.getByText('Warning')).toBeInTheDocument()
  const warningRow = screen.getByText('Warning').closest('tr')!
  expect(warningRow).toHaveTextContent('80')
})

test('clicking a horizontal line eye emits update:hiddenLineNames with that name added', async () => {
  const line: HorizontalLine = {
    name: 'scalar_of(warning,rrd_metric(h/svc/util))',
    title: 'Warning',
    value: 80,
    color: '#ffaa00'
  }
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU], horizontalLines: [line], hiddenLineNames: [] }
  })
  const warningRow = screen.getByText('Warning').closest('tr')!
  await fireEvent.click(warningRow.querySelector('button')!)
  expect(emitted()['update:hiddenLineNames']).toEqual([
    [['scalar_of(warning,rrd_metric(h/svc/util))']]
  ])
})

test('clicking a hidden horizontal line eye emits update:hiddenLineNames with that name removed', async () => {
  const line: HorizontalLine = {
    name: 'scalar_of(warning,rrd_metric(h/svc/util))',
    title: 'Warning',
    value: 80,
    color: '#ffaa00'
  }
  const { emitted } = render(GraphLegend, {
    props: {
      metrics: [CPU],
      horizontalLines: [line],
      hiddenLineNames: ['scalar_of(warning,rrd_metric(h/svc/util))']
    }
  })
  const warningRow = screen.getByText('Warning').closest('tr')!
  await fireEvent.click(warningRow.querySelector('button')!)
  expect(emitted()['update:hiddenLineNames']).toEqual([[[]]])
})

test('reverses consecutive metrics sharing a stack id, leaving unstacked metrics and stack order untouched', () => {
  const a = makeMetricWithStack('a', 'A', null)
  const b = makeMetricWithStack('b', 'B', 's1')
  const c = makeMetricWithStack('c', 'C', 's1')
  const d = makeMetricWithStack('d', 'D', 's1')
  const e = makeMetricWithStack('e', 'E', null)
  const f = makeMetricWithStack('f', 'F', 's2')
  const g = makeMetricWithStack('g', 'G', 's2')
  const { container } = render(GraphLegend, { props: { metrics: [a, b, c, d, e, f, g] } })
  const names = Array.from(container.querySelectorAll('.graphing-graph-legend__name')).map((el) =>
    el.textContent?.trim()
  )
  expect(names).toEqual(['A', 'D', 'C', 'B', 'E', 'G', 'F'])
})

test('lists a stack top-to-bottom in the same order computeStackedSeries draws it bottom-to-top', () => {
  const first = makeMetricWithStack('first', 'First', 's1')
  const second = makeMetricWithStack('second', 'Second', 's1')
  const third = makeMetricWithStack('third', 'Third', 's1')
  const metrics = [first, second, third]
  const buckets = metrics.map(() => [makeBucket(1)])

  const series = computeStackedSeries(metrics, buckets, 'avg')
  const topmostIndex = series.reduce(
    (topIdx, current, idx) =>
      current.bands[0]!.upper > series[topIdx]!.bands[0]!.upper ? idx : topIdx,
    0
  )
  const topmostTitle = metrics[topmostIndex]!.metadata.title

  const { container } = render(GraphLegend, { props: { metrics } })
  const firstRowTitle = container.querySelector('.graphing-graph-legend__name')!.textContent?.trim()

  expect(firstRowTitle).toBe(topmostTitle)
})

test('clicking "hide all" emits update:hiddenMetricNames with every metric name', async () => {
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU, MEM], hiddenMetricNames: [] }
  })
  await fireEvent.click(screen.getByRole('button', { name: /hide all/i }))
  expect(emitted()['update:hiddenMetricNames']).toEqual([[['cpu', 'mem']]])
})

test('clicking "show all" when every metric is already hidden emits update:hiddenMetricNames with an empty list', async () => {
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU, MEM], hiddenMetricNames: ['cpu', 'mem'] }
  })
  await fireEvent.click(screen.getByRole('button', { name: /show all/i }))
  expect(emitted()['update:hiddenMetricNames']).toEqual([[[]]])
})

test('marks header and horizontal-line rows as padded once the metrics table overflows its scroll container', async () => {
  const line: HorizontalLine = {
    name: 'scalar_of(warning,rrd_metric(h/svc/util))',
    title: 'Warning',
    value: 80,
    color: '#ffaa00'
  }
  const { container } = render(GraphLegend, {
    props: { metrics: [CPU, MEM], horizontalLines: [line] }
  })

  const metricsTable = container.querySelector('.graphing-graph-legend__table-metrics')!
  const scrollContainer = metricsTable.parentElement!
  Object.defineProperty(scrollContainer, 'scrollHeight', { value: 500, configurable: true })
  Object.defineProperty(scrollContainer, 'clientHeight', { value: 100, configurable: true })

  const headerRow = container.querySelector('.graphing-graph-legend__header-row')!
  await waitFor(() => expect(headerRow).toHaveClass('graphing-graph-legend__padded-row'))
  const lineRow = screen.getByText('Warning').closest('tr')!
  expect(lineRow).toHaveClass('graphing-graph-legend__padded-row')
})

test('does not mark rows as padded when the metrics table fits without scrolling', async () => {
  const { container } = render(GraphLegend, { props: { metrics: [CPU, MEM] } })
  await nextTick()
  await nextTick()
  const headerRow = container.querySelector('.graphing-graph-legend__header-row')!
  expect(headerRow).not.toHaveClass('graphing-graph-legend__padded-row')
})

test('observes both the metrics table and its scroll container for resizes', async () => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
  const { container } = render(GraphLegend, { props: { metrics: [CPU, MEM] } })
  await nextTick()

  const metricsTable = container.querySelector('.graphing-graph-legend__table-metrics')!
  const observedTargets = FakeResizeObserver.instances.flatMap((observer) => observer.observed)
  expect(observedTargets).toContain(metricsTable)
  expect(observedTargets).toContain(metricsTable.parentElement)
})

test('caps the metric rows at 500px by default', () => {
  const { container } = render(GraphLegend, { props: { metrics: [CPU, MEM] } })
  expect(container.querySelector('.graphing-graph-legend--fill')).not.toBeInTheDocument()
  const scroll = container.querySelector<HTMLElement>('.graphing-graph-legend__rows-scroll')!
  expect(scroll.style.maxHeight).toBe('500px')
})

test('fillHeight applies the fill modifier and lifts the metric-rows height cap', () => {
  const { container } = render(GraphLegend, { props: { metrics: [CPU, MEM], fillHeight: true } })
  expect(container.querySelector('.graphing-graph-legend--fill')).toBeInTheDocument()
  const scroll = container.querySelector<HTMLElement>('.graphing-graph-legend__rows-scroll')!
  expect(scroll.style.maxHeight).toBe('none')
})

test('recomputes padded rows when the scroll container is resized', async () => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
  const { container } = render(GraphLegend, { props: { metrics: [CPU, MEM] } })
  await nextTick()

  const headerRow = container.querySelector('.graphing-graph-legend__header-row')!
  expect(headerRow).not.toHaveClass('graphing-graph-legend__padded-row')

  const metricsTable = container.querySelector('.graphing-graph-legend__table-metrics')!
  const scrollContainer = metricsTable.parentElement!
  Object.defineProperty(scrollContainer, 'scrollHeight', { value: 500, configurable: true })
  Object.defineProperty(scrollContainer, 'clientHeight', { value: 100, configurable: true })

  const observer = FakeResizeObserver.instances.find((candidate) =>
    candidate.observed.includes(scrollContainer)
  )!
  observer.callback([], observer as unknown as ResizeObserver)
  await nextTick()

  expect(headerRow).toHaveClass('graphing-graph-legend__padded-row')
})
