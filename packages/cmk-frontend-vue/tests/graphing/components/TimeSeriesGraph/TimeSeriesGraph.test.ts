/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import TimeSeriesGraph from '@/graphing/components/TimeSeriesGraph/TimeSeriesGraph.vue'
import { measureAxisLabel } from '@/graphing/components/TimeSeriesGraph/axes/labelWidth'
import type { Metric, TimeSeriesGraphProps } from '@/graphing/components/TimeSeriesGraph/types'
import { AXIS_CLASSES } from '@/graphing/components/TimeSeriesGraph/useAxes'
import {
  CANVAS_MARGIN_LEFT,
  PLOT_INSET_X,
  VALUE_LABEL_TICK_OFFSET
} from '@/graphing/components/constants'

let drawnPoints: Array<[number, number]> = []

// jsdom implements neither a 2D canvas context nor matchMedia, both of which the graph
// touches on mount (draw() + the devicePixelRatio watcher). Stub them so the component
// mounts and runs its real draw path instead of throwing.
function createCanvasContextStub(): CanvasRenderingContext2D {
  const state: Record<string | symbol, unknown> = {}
  const recordPoint = (x: number, y: number): void => void drawnPoints.push([x, y])
  return new Proxy(state, {
    get: (target, prop) => {
      if (prop === 'moveTo' || prop === 'lineTo') {
        return recordPoint
      }
      return prop in target ? target[prop] : () => undefined
    },
    set: (target, prop, value) => {
      target[prop] = value
      return true
    }
  }) as unknown as CanvasRenderingContext2D
}

beforeEach(() => {
  drawnPoints = []
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
  view_time_range: { start: 1_000, end: 2_000, step: 60 },
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
  options: { ...DEFAULT_PROPS.options, y_axis: { unit: IEC_UNIT } }
}

function drawnXs(): number[] {
  return drawnPoints.map(([x]) => x)
}

function plotWidthPx(): number {
  return parseFloat(document.querySelector('canvas')!.style.width)
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

async function renderMemoryGraph(
  props: Partial<TimeSeriesGraphProps> = {}
): Promise<{ margin: number; widestLabel: number }> {
  const { container } = renderComponent({ ...MEMORY_PROPS, ...props })
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

function plotCanvasStyle(container: Element): CSSStyleDeclaration {
  return within(container as HTMLElement).getByRole('img').style
}

// What the figure keeps between the plot's edge and its own, read back off the rendered plot.
function plotInsets(container: Element): {
  left: number
  right: number
  top: number
  bottom: number
} {
  const style = plotCanvasStyle(container)
  const left = parseFloat(style.left)
  const top = parseFloat(style.top)
  return {
    left,
    right: DEFAULT_PROPS.size.width - left - parseFloat(style.width),
    top,
    bottom: DEFAULT_PROPS.size.height - top - parseFloat(style.height)
  }
}

function timeAxisLabels(container: Element): string[] {
  return Array.from(container.querySelectorAll(`g.${AXIS_CLASSES.timeLabels} text`)).map(
    (tickLabel) => tickLabel.textContent ?? ''
  )
}

function drawnValueAxisLabels(container: Element): string[] {
  return valueAxisLabels(container).filter((label) => label !== '')
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

  const VIEW_TIME_RANGE = { start: 1_060, end: 1_180, step: 60 }
  const DATA_TIME_RANGE_REACHING_PAST_THE_VIEW = { start: 940, end: 1_240, step: 60 }
  const SAMPLES_REACHING_PAST_THE_VIEW = [1, 2, 3, 4, 5]
  const COLUMN_WIDTH_PX = 1

  test('draws the curve out past the leading edge when the data reaches beyond it', async () => {
    const metrics = [{ ...LINE_METRIC, data_points: SAMPLES_REACHING_PAST_THE_VIEW }]

    renderComponent({
      view_time_range: VIEW_TIME_RANGE,
      data_time_range: DATA_TIME_RANGE_REACHING_PAST_THE_VIEW,
      metrics
    })
    await waitFor(() => expect(drawnPoints.length).toBeGreaterThan(0))

    expect(Math.min(...drawnXs())).toBeLessThan(0)
  })

  test('draws the curve out past the trailing edge when the data reaches beyond it', async () => {
    const metrics = [{ ...LINE_METRIC, data_points: SAMPLES_REACHING_PAST_THE_VIEW }]

    renderComponent({
      view_time_range: VIEW_TIME_RANGE,
      data_time_range: DATA_TIME_RANGE_REACHING_PAST_THE_VIEW,
      metrics
    })
    await waitFor(() => expect(drawnPoints.length).toBeGreaterThan(0))

    expect(Math.max(...drawnXs())).toBeGreaterThan(plotWidthPx())
  })

  test('reaches the right edge when the newest interval has not closed yet', async () => {
    const dataTimeRangeReachingPastThePresent = { start: 940, end: 1_300, step: 60 }
    const samplesWithTheTwoNewestIntervalsStillOpen = [1, 2, 3, 4, null, null]
    const metrics = [{ ...LINE_METRIC, data_points: samplesWithTheTwoNewestIntervalsStillOpen }]

    renderComponent({
      view_time_range: VIEW_TIME_RANGE,
      data_time_range: dataTimeRangeReachingPastThePresent,
      metrics
    })
    await waitFor(() => expect(drawnPoints.length).toBeGreaterThan(0))

    expect(Math.max(...drawnXs())).toBeGreaterThanOrEqual(plotWidthPx() - COLUMN_WIDTH_PX)
  })

  function rightmostDrawnXOnPlot(stack: string | null): number {
    drawnPoints = []
    const metrics = [
      {
        ...LINE_METRIC,
        render: { ...LINE_METRIC.render, stack },
        data_points: SAMPLES_REACHING_PAST_THE_VIEW
      }
    ]
    const { unmount } = renderComponent({
      view_time_range: VIEW_TIME_RANGE,
      data_time_range: DATA_TIME_RANGE_REACHING_PAST_THE_VIEW,
      metrics
    })
    const onPlot = drawnXs().filter((x) => x <= plotWidthPx() + 0.01)
    unmount()
    return Math.max(...onPlot)
  }

  test('ends an area series where the line series ends', () => {
    const asLine = rightmostDrawnXOnPlot(null)

    const asArea = rightmostDrawnXOnPlot('area')

    expect(asArea).toBeCloseTo(asLine, 5)
  })

  test('keeps the value axis off a spike that only the off-screen neighbours carry', async () => {
    const offViewSpike = 1_000
    const samplesSpikingOnlyOutsideTheView = [offViewSpike, 2, 3, 4, offViewSpike]
    const metrics = [{ ...LINE_METRIC, data_points: samplesSpikingOnlyOutsideTheView }]

    const { container } = renderComponent({
      view_time_range: VIEW_TIME_RANGE,
      data_time_range: DATA_TIME_RANGE_REACHING_PAST_THE_VIEW,
      metrics
    })
    await waitFor(() => expect(valueAxisLabels(container)).not.toHaveLength(0))

    expect(valueAxisLabels(container)).not.toContain(String(offViewSpike))
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
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 200, clientY: 50 }))
    window.dispatchEvent(new MouseEvent('mouseup', { clientX: 200, clientY: 50 }))

    expect(await screen.findByRole('status')).toHaveTextContent('Maximum zoom reached')
  })

  test('draws both axes when their visibility is left unspecified', async () => {
    const { container } = renderComponent()

    expect(timeAxisLabels(container)).not.toHaveLength(0)
    await waitFor(() => {
      expect(drawnValueAxisLabels(container)).not.toHaveLength(0)
    })
  })

  test('a hidden time axis drops its labels and gives the bottom margin to the plot', async () => {
    const shown = renderComponent({ showTimeAxis: true })
    const shownHeight = plotCanvasStyle(shown.container).height

    const hidden = renderComponent({ showTimeAxis: false })

    expect(timeAxisLabels(shown.container)).not.toHaveLength(0)
    expect(timeAxisLabels(hidden.container)).toHaveLength(0)
    await waitFor(() => {
      expect(parseFloat(plotCanvasStyle(hidden.container).height)).toBeGreaterThan(
        parseFloat(shownHeight)
      )
    })
  })

  test('a hidden value axis gives its room to the plot but keeps the frame padding', async () => {
    const shown = renderComponent({ showValueAxis: true })
    const shownWidth = plotCanvasStyle(shown.container).width

    const hidden = renderComponent({ showValueAxis: false })

    await waitFor(() => {
      expect(drawnValueAxisLabels(shown.container)).not.toHaveLength(0)
    })
    expect(drawnValueAxisLabels(hidden.container)).toHaveLength(0)
    await waitFor(() => {
      const insets = plotInsets(hidden.container)
      expect(insets.left).toBe(insets.right)
      expect(parseFloat(plotCanvasStyle(hidden.container).width)).toBeGreaterThan(
        parseFloat(shownWidth)
      )
    })
  })

  test('a plot with both axes hidden sits centred in the figure', async () => {
    const { container } = renderComponent({ showTimeAxis: false, showValueAxis: false })

    await waitFor(() => {
      const insets = plotInsets(container)
      expect(insets.left).toBe(insets.right)
      expect(insets.top).toBe(insets.bottom)
    })
  })

  test('a hidden time axis still leaves the shown value axis room for its lowest label', async () => {
    const { container } = renderComponent({ showTimeAxis: false, showValueAxis: true })

    await waitFor(() => {
      const style = plotCanvasStyle(container)
      expect(parseFloat(style.top) + parseFloat(style.height)).toBeLessThan(
        DEFAULT_PROPS.size.height
      )
    })
  })

  test('gives the value axis the width it was configured for, beside the padding', async () => {
    const configuredWidth = 120

    const { container } = renderComponent({ minValueAxisWidth: configuredWidth })

    await waitFor(() => {
      const insets = plotInsets(container)
      expect(insets.left - insets.right).toBe(configuredWidth)
    })
  })

  test('widens the configured value axis width for labels that do not fit it', async () => {
    const { margin, widestLabel } = await renderMemoryGraph({ minValueAxisWidth: 1 })

    expect(margin).toBeGreaterThanOrEqual(widestLabel + VALUE_LABEL_TICK_OFFSET + PLOT_INSET_X)
  })

  test('a hidden time axis takes the pan affordances with it', () => {
    renderComponent({ showTimeAxis: false, panEnabled: true })

    expect(screen.queryByRole('button', { name: 'Step back in time' })).not.toBeInTheDocument()
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

    expect(margin).toBeGreaterThanOrEqual(widestLabel + VALUE_LABEL_TICK_OFFSET + PLOT_INSET_X)
    expect(margin).toBeGreaterThan(CANVAS_MARGIN_LEFT)
  })

  test('sizes the value axis to labels the theme letter-spaces', async () => {
    const unspaced = await renderMemoryGraph()

    letterSpaceEveryElement()
    const spaced = await renderMemoryGraph()

    expect(spaced.margin).toBeGreaterThan(unspaced.margin)
    expect(spaced.margin).toBeGreaterThanOrEqual(
      spaced.widestLabel + VALUE_LABEL_TICK_OFFSET + PLOT_INSET_X
    )
  })
})

describe('TimeSeriesGraph — the pin and the plot size', () => {
  // The handle stands above the plot rather than inside it, so arming the pin must not cost
  // plot height: GraphFigure floors a widget at 50px, which leaves nothing to give away.
  const SHORT_FIGURE = { width: 400, height: 50, mode: 'fixed' } as const
  const MARGIN_TOP = 4

  function plotHeightPx(): number {
    return parseFloat(document.querySelector('canvas')!.style.height)
  }

  test('arming the pin leaves a figure at the dashboard floor untouched', () => {
    renderComponent({ size: SHORT_FIGURE, pinEnabled: false })
    const withoutPin = plotHeightPx()
    document.body.innerHTML = ''
    renderComponent({ size: SHORT_FIGURE, pinEnabled: true })

    expect(plotHeightPx()).toBeGreaterThan(0)
    expect(plotHeightPx()).toBe(withoutPin)
  })

  // Drawn upwards from the edge it is anchored on, so its top is what keeps it clear.
  test('the pin handle is anchored on the plot top edge, not inside the plot', () => {
    renderComponent({ size: SHORT_FIGURE, pinEnabled: true, pinTime: 1_500 })

    const handle = document.querySelector('.graphing-pin-handle')
    expect(handle).toBeInTheDocument()
    expect((handle as HTMLElement).style.top).toBe(`${MARGIN_TOP}px`)
  })

  test('a tall figure is sized the same with and without the pin', () => {
    const tall = { width: 400, height: 300, mode: 'fixed' } as const
    renderComponent({ size: tall, pinEnabled: false })
    const withoutPin = plotHeightPx()
    document.body.innerHTML = ''
    renderComponent({ size: tall, pinEnabled: true })

    expect(plotHeightPx()).toBe(withoutPin)
  })
})

describe('TimeSeriesGraph — placing the pin by clicking the plot', () => {
  // jsdom reports a zero-origin rect, so client coordinates are plot coordinates.
  function pressPlot(from: { x: number; y: number }, travelPx: number): void {
    const canvas = document.querySelector('canvas')!
    void fireEvent.mouseDown(canvas, { button: 0, clientX: from.x, clientY: from.y })
    if (travelPx !== 0) {
      window.dispatchEvent(
        new MouseEvent('mousemove', { clientX: from.x + travelPx, clientY: from.y })
      )
    }
    window.dispatchEvent(new MouseEvent('mouseup', { clientX: from.x + travelPx, clientY: from.y }))
  }

  const clickPlot = (at: { x: number; y: number }): void => pressPlot(at, 0)

  test('a click in the plot pins the sample under the cursor', async () => {
    const { emitted } = renderComponent({ pinEnabled: true })

    clickPlot({ x: 200, y: 100 })

    await waitFor(() => expect(emitted()).toHaveProperty('pinCreate'))
    const [payload] = (emitted()['pinCreate'] as Array<[{ time: number }]>)[0]!
    expect(payload.time).toBeGreaterThanOrEqual(DEFAULT_PROPS.view_time_range.start)
    expect(payload.time).toBeLessThanOrEqual(DEFAULT_PROPS.view_time_range.end)
  })

  test('a drag past the threshold zooms instead of pinning', () => {
    const { emitted } = renderComponent({ pinEnabled: true })

    pressPlot({ x: 200, y: 100 }, 80)

    expect(emitted()).not.toHaveProperty('pinCreate')
    expect(emitted()).toHaveProperty('zoom')
  })

  // The hint answers an attempted zoom, which a click at the floor is not.
  test('a click at maximum zoom pins without reporting a refused zoom', async () => {
    const { emitted } = renderComponent({ pinEnabled: true, atMinTimeZoom: true })

    clickPlot({ x: 200, y: 100 })

    await waitFor(() => expect(emitted()).toHaveProperty('pinCreate'))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  test('a drag at maximum zoom still reports the refused zoom', async () => {
    renderComponent({ pinEnabled: true, atMinTimeZoom: true })

    pressPlot({ x: 200, y: 100 }, 80)

    expect(await screen.findByRole('status')).toHaveTextContent('Maximum zoom reached')
  })

  test('a graph whose pin is disabled ignores the click', () => {
    const { emitted } = renderComponent({ pinEnabled: false })

    clickPlot({ x: 200, y: 100 })

    expect(emitted()).not.toHaveProperty('pinCreate')
  })

  describe('explicit value range', () => {
    // A range the data (between 1 and 5) can never produce, so any tick reaching it proves the
    // axis was forced onto the explicit range rather than derived from the data. Symmetric bounds
    // so d3's ticks land on the endpoints regardless of the chosen step.
    const EXPLICIT_RANGE = { min: -40, max: 40 }

    // Empty tick texts appear mid-transition; Number('') is 0, not NaN, so they must be
    // dropped before parsing or they would spuriously pull the min down to zero.
    function numericTicks(container: Element): number[] {
      return valueAxisLabels(container)
        .filter((label) => label.trim() !== '')
        .map((label) => Number(label))
        .filter((value) => !Number.isNaN(value))
    }

    test('forces the value domain onto the explicit range, past the data extent', async () => {
      const { container } = renderComponent({
        metrics: [LINE_METRIC],
        options: {
          ...DEFAULT_PROPS.options,
          y_axis: { unit: UNIT, explicit_range: EXPLICIT_RANGE }
        },
        valueRange: null
      })

      // Tick text lands when the d3 axis transition starts, hence the waitFor.
      await waitFor(() => {
        const ticks = numericTicks(container)
        // The data never goes negative nor above 5; only the forced range reaches here.
        expect(Math.min(...ticks)).toBeLessThan(0)
        expect(Math.max(...ticks)).toBeGreaterThanOrEqual(40)
      })
    })

    test('lets a zoom value range take precedence over the configured explicit range', async () => {
      const { container } = renderComponent({
        metrics: [LINE_METRIC],
        options: {
          ...DEFAULT_PROPS.options,
          y_axis: { unit: UNIT, explicit_range: EXPLICIT_RANGE }
        },
        // A value-zoom is active: it must win, collapsing the axis back towards [1, 5] - these
        // are not necessarily the exact bounds of the axis, as they are aligned through the tick
        // step.
        valueRange: { min: 1, max: 5 }
      })

      await waitFor(() => {
        const ticks = numericTicks(container)
        expect(ticks.length).toBeGreaterThan(0)
        // Test for [0, 6] instead of [1, 5] as the y-axis bounds are aligned not forced to the
        // zoom's value range.
        expect(Math.min(...ticks)).toBeGreaterThanOrEqual(0)
        expect(Math.max(...ticks)).toBeLessThanOrEqual(6)
      })
    })
  })
})
