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
const LINE_UNIT: HorizontalLine['unit'] = {
  notation: 'decimal',
  symbol: '%',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

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
const WARN_LINE: HorizontalLine = {
  name: 'scalar_of(warning,rrd_metric(h/svc/util))',
  title: 'Warning',
  value: 80,
  unit: LINE_UNIT,
  color: '#ffaa00'
}
const CRIT_LINE: HorizontalLine = {
  name: 'scalar_of(critical,rrd_metric(h/svc/util))',
  title: 'Critical',
  value: 90,
  unit: LINE_UNIT,
  color: '#ff0000'
}

test('renders one row per metric', () => {
  render(GraphLegend, { props: { metrics: [CPU, MEM] } })
  expect(screen.getByText('CPU')).toBeInTheDocument()
  expect(screen.getByText('Memory')).toBeInTheDocument()
})

test('clicking the metric count hides every metric', async () => {
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU, MEM], hiddenMetricNames: [] }
  })
  await fireEvent.click(screen.getByRole('button', { name: /2 metrics/ }))
  expect(emitted()['update:hiddenMetricNames']).toEqual([[['cpu', 'mem']]])
})

test('clicking the metric count with everything hidden shows every metric', async () => {
  const { emitted } = render(GraphLegend, {
    props: { metrics: [CPU, MEM], hiddenMetricNames: ['cpu', 'mem'] }
  })
  await fireEvent.click(screen.getByRole('button', { name: /2 metrics/ }))
  expect(emitted()['update:hiddenMetricNames']).toEqual([[[]]])
})

test('the count states how many of the metrics are currently visible', () => {
  const metrics = Array.from({ length: 26 }, (_, i) => makeMetric(`m${i}`, `Metric ${i}`, [i]))
  render(GraphLegend, {
    props: { metrics, hiddenMetricNames: metrics.slice(3).map((m) => m.metadata.name) }
  })

  expect(screen.getByText('3 of 26 metrics are visible')).toBeInTheDocument()
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

test('horizontal lines render their value with their unit, as metric values are', () => {
  const line: HorizontalLine = {
    name: 'scalar_of(warning,rrd_metric(h/svc/util))',
    title: 'Warning',
    value: 80,
    unit: LINE_UNIT,
    color: '#ffaa00'
  }
  render(GraphLegend, { props: { metrics: [CPU], horizontalLines: [line] } })
  expect(screen.getByText('Warning')).toBeInTheDocument()
  const warningRow = screen.getByText('Warning').closest('tr')!
  // Not the bare '80': a threshold is read against the metric it bounds, so it carries its unit.
  expect(warningRow).toHaveTextContent(/80\s*%/)
})

test('clicking a horizontal line eye emits update:hiddenLineNames with that name added', async () => {
  const line: HorizontalLine = {
    name: 'scalar_of(warning,rrd_metric(h/svc/util))',
    title: 'Warning',
    value: 80,
    unit: LINE_UNIT,
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
    unit: LINE_UNIT,
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
    unit: LINE_UNIT,
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

function metricRowsMaxHeightPx(container: Element): number {
  const scroller = container.querySelector<HTMLElement>('.graphing-graph-legend__rows-scroll')
  return Number.parseInt(scroller!.style.maxHeight, 10)
}

test('caps the metric rows at seven rows by default', () => {
  const { container } = render(GraphLegend, { props: { metrics: [CPU, MEM] } })
  expect(container.querySelector('.graphing-graph-legend--fill')).not.toBeInTheDocument()
  expect(metricRowsMaxHeightPx(container)).toBe(7 * 24)
})

test('the row height the cap is derived from reaches the stylesheet', () => {
  const { container } = render(GraphLegend, { props: { metrics: [CPU, MEM] } })

  // The rows take their height from the same constant the cap multiplies. Were the two to
  // drift apart, the cap would stop landing on a row boundary.
  const root = container.querySelector<HTMLElement>('.graphing-graph-legend')!
  expect(root.style.getPropertyValue('--legend-row-height')).toBe('24px')
})

test('threshold lines eat into the same seven-item budget', () => {
  const { container } = render(GraphLegend, {
    props: { metrics: [CPU, MEM], horizontalLines: [WARN_LINE, CRIT_LINE] }
  })

  expect(metricRowsMaxHeightPx(container)).toBe(5 * 24)
})

test('the metric rows keep room for one row even when thresholds outnumber the budget', () => {
  const manyLines = Array.from({ length: 9 }, (_, i) => ({ ...WARN_LINE, name: `Line ${i}` }))
  const { container } = render(GraphLegend, {
    props: { metrics: [CPU, MEM], horizontalLines: manyLines }
  })

  expect(metricRowsMaxHeightPx(container)).toBe(24)
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
