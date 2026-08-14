/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import TimeSeriesGraph from '@/graphing/components/TimeSeriesGraph/TimeSeriesGraph.vue'
import { measureAxisLabel } from '@/graphing/components/TimeSeriesGraph/axes/labelWidth'
import type { Metric, TimeSeriesGraphProps } from '@/graphing/components/TimeSeriesGraph/types'
import { CANVAS_MARGIN_LEFT, VALUE_LABEL_GUTTER } from '@/graphing/components/constants'

// jsdom implements neither a 2D canvas context nor matchMedia, both of which the graph
// touches on mount (draw() + the devicePixelRatio watcher). Stub them so the component
// mounts and runs its real draw path instead of throwing.
function createCanvasContextStub(): CanvasRenderingContext2D {
  const state: Record<string | symbol, unknown> = {}
  return new Proxy(state, {
    get: (target, prop) => (prop in target ? target[prop] : () => undefined),
    set: (target, prop, value) => {
      target[prop] = value
      return true
    }
  }) as unknown as CanvasRenderingContext2D
}

beforeEach(() => {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    })
  )
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(createCanvasContextStub())
})

let themeLetterSpacing: HTMLStyleElement | null = null

function letterSpaceEveryElement(): void {
  themeLetterSpacing = document.createElement('style')
  themeLetterSpacing.textContent = '* { letter-spacing: 0.5px; }'
  document.head.appendChild(themeLetterSpacing)
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  themeLetterSpacing?.remove()
  themeLetterSpacing = null
})

const UNIT: components['schemas']['ApiUnitFormat'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

// stack: null makes computeStackedSeries classify the metric as a 'line' series (rather than
// a stacked area), so this fixture is genuinely a line graph.
const LINE_METRIC: Metric = {
  metadata: { name: 'cpu', title: 'CPU utilization', unit: UNIT, color: '#ff0000' },
  render: { stack: null, inverse: false, hidden: false },
  data_points: [1, 2, 3, 4, 5]
}

const STACKED_METRIC: Metric = {
  metadata: { name: 'user', title: 'User', unit: UNIT, color: '#00ff00' },
  render: { stack: 'area', inverse: false, hidden: false },
  data_points: [1, 2, 3, 4, 5]
}

// inverse mirrors the metric below the baseline, which forces the y-domain symmetric
// around zero.
const INVERSE_METRIC: Metric = {
  metadata: { name: 'if_out', title: 'Output bandwidth', unit: UNIT, color: '#0000ff' },
  render: { stack: null, inverse: true, hidden: false },
  data_points: [1, 2, 3, 4, 5]
}

const DEFAULT_PROPS: TimeSeriesGraphProps = {
  size: { width: 800, height: 400, mode: 'fixed' },
  options: {
    header: { title: null, show_graph_time: false },
    name: 'graph',
    x_axis: null,
    y_axis: null,
    font_size_pt: 10
  },
  time_range: { start: 1_000, end: 2_000, step: 60 },
  metrics: [LINE_METRIC],
  horizontal_lines: [],
  valueRange: null,
  zoomMode: 'time',
  minTimeRange: null,
  minValueRange: null,
  inspecting: false,
  panEnabled: false,
  zoomEnabled: false,
  highlightedMetricName: null
}

function renderComponent(props: Partial<TimeSeriesGraphProps> = {}) {
  return render(TimeSeriesGraph, { props: { ...DEFAULT_PROPS, ...props } })
}

const IEC_UNIT: components['schemas']['ApiUnitFormat'] = {
  notation: 'iec',
  symbol: 'B',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}
const MEMORY_METRIC: Metric = {
  metadata: { name: 'mem_used', title: 'RAM used', unit: IEC_UNIT, color: '#ff0000' },
  render: { stack: null, inverse: false, hidden: false },
  data_points: [1.2e9, 1.4e9, 1.6e9, 1.8e9, 2.0e9]
}
const MEMORY_PROPS: Partial<TimeSeriesGraphProps> = {
  metrics: [MEMORY_METRIC],
  options: { ...DEFAULT_PROPS.options, y_axis: { title: '', unit: IEC_UNIT } }
}

function valueAxisGroup(container: Element): Element {
  const axis = container.querySelector('g.graphing-time-series-graph__y-axis')
  if (axis?.parentElement === null || axis?.parentElement === undefined) {
    throw new Error('the value axis has not been drawn')
  }
  return axis.parentElement
}

function valueAxisMargin(container: Element): number {
  const transform = valueAxisGroup(container).getAttribute('transform') ?? ''
  return Number(/translate\(([\d.]+),/.exec(transform)?.[1])
}

function valueAxisLabels(container: Element): string[] {
  return Array.from(
    container.querySelectorAll('g.graphing-time-series-graph__y-axis .tick text')
  ).map((tickLabel) => tickLabel.textContent ?? '')
}

async function renderMemoryGraph(): Promise<{ margin: number; widestLabel: number }> {
  const { container } = renderComponent(MEMORY_PROPS)
  await waitFor(() => {
    expect(valueAxisLabels(container).filter((label) => label !== '')).not.toHaveLength(0)
  })
  const reference = valueAxisGroup(container)
  return {
    margin: valueAxisMargin(container),
    widestLabel: Math.max(
      ...valueAxisLabels(container).map((label) => measureAxisLabel(label, reference))
    )
  }
}

describe('TimeSeriesGraph', () => {
  test('mounts a line graph with a canvas drawing surface', () => {
    const metrics = [LINE_METRIC]

    renderComponent({ metrics })

    // The plot surface is exposed to assistive tech as an image named after the metric
    // (no configured graph title), and that surface must be the data canvas.
    const plotSurface = screen.getByRole('img', { name: 'CPU utilization' })
    expect(plotSurface.tagName).toBe('CANVAS')
  })

  test('prefers the configured graph title over metric titles for the plot accessible name', () => {
    const options = {
      ...DEFAULT_PROPS.options,
      header: { title: 'CPU overview', show_graph_time: false }
    }

    renderComponent({ metrics: [LINE_METRIC], options })

    expect(screen.getByRole('img', { name: 'CPU overview' })).toBeInTheDocument()
  })

  test('mounts a stacked-area graph with the y-axis path in the SVG layer', () => {
    const metrics = [STACKED_METRIC]

    const { container } = renderComponent({ metrics })

    // D3's axisLeft inserts the domain path synchronously; only its geometry is animated.
    expect(
      container.querySelector('svg g.graphing-time-series-graph__y-axis path.domain')
    ).toBeInTheDocument()
  })

  test('says nothing about the zoom floor until a drag is actually refused', () => {
    renderComponent({ zoomEnabled: true, minTimeRange: 60, atMinTimeZoom: true })

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  // The hint answers a gesture, not a hover, so it has to appear on the press alone with no
  // pointer resting anywhere for it to attach to.
  test('states the reason when a zoom is refused at the time floor', async () => {
    renderComponent({ zoomEnabled: true, minTimeRange: 60, atMinTimeZoom: true })

    await fireEvent.mouseDown(screen.getByRole('img', { name: 'CPU utilization' }), {
      button: 0,
      clientX: 100,
      clientY: 50
    })

    expect(await screen.findByRole('status')).toHaveTextContent('Maximum zoom reached')
  })

  test('labels the y-axis on both sides of zero for a mirrored metric', async () => {
    const metrics = [INVERSE_METRIC]

    const { container } = renderComponent({ metrics })

    // Tick label text is applied when the d3 axis transition starts, hence the waitFor.
    await waitFor(() => {
      const tickValues = Array.from(
        container.querySelectorAll('g.graphing-time-series-graph__y-axis .tick text')
      ).map((tickLabel) => Number(tickLabel.textContent))
      expect(tickValues.some((value) => value < 0)).toBe(true)
      expect(tickValues.some((value) => value > 0)).toBe(true)
    })
  })

  test('sizes the value axis to hold its widest label', async () => {
    const { margin, widestLabel } = await renderMemoryGraph()

    expect(margin).toBeGreaterThanOrEqual(widestLabel + VALUE_LABEL_GUTTER)
    expect(margin).toBeGreaterThan(CANVAS_MARGIN_LEFT)
  })

  test('sizes the value axis to labels the theme letter-spaces', async () => {
    const unspaced = await renderMemoryGraph()

    letterSpaceEveryElement()
    const spaced = await renderMemoryGraph()

    expect(spaced.margin).toBeGreaterThan(unspaced.margin)
    expect(spaced.margin).toBeGreaterThanOrEqual(spaced.widestLabel + VALUE_LABEL_GUTTER)
  })
})
