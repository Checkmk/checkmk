/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ScaleLinear, ScaleTime } from 'd3-scale'

import type { M4Bucket } from '../decimation/types'
import type { Metric } from '../types'
import { keptSamples } from './bucket'
import { type TimeValuePoint, valueAt } from './polyline'

export interface StackedVertex {
  time: number
  lower: number
  upper: number
}

export interface StackedColumn {
  gap: boolean
  vertices: StackedVertex[]
}

export interface LineSeries {
  kind: 'line'
}

export interface AreaSeries {
  kind: 'area-stacked'
  columns: StackedColumn[]
}

export type StackedSeries = LineSeries | AreaSeries
export type StackedSeriesKind = StackedSeries['kind']

type EdgePerColumn = TimeValuePoint[][]

export function computeStackedSeries(
  metrics: Metric[],
  metricsBuckets: M4Bucket[][]
): StackedSeries[] {
  const upperEdgeOfStack = new Map<string, EdgePerColumn>()

  return metrics.map((metric, metricIndex) => {
    const stack = metric.render.stack
    if (stack === null) {
      return { kind: 'line' }
    }
    const buckets = metricsBuckets[metricIndex]!
    const edgeBelow = upperEdgeOfStack.get(stack) ?? buckets.map(() => [])
    const columns = buckets.map((bucket, columnIndex) =>
      stackColumn(keptSamples(bucket), edgeBelow[columnIndex] ?? [])
    )
    upperEdgeOfStack.set(
      stack,
      columns.map((column, columnIndex) =>
        column.gap ? (edgeBelow[columnIndex] ?? []) : upperEdgeOf(column)
      )
    )
    return { kind: 'area-stacked', columns }
  })
}

function stackColumn(samples: TimeValuePoint[], edgeBelow: TimeValuePoint[]): StackedColumn {
  if (samples.length === 0) {
    return { gap: true, vertices: [] }
  }
  const lowerAt = (time: number): number => (edgeBelow.length === 0 ? 0 : valueAt(edgeBelow, time))
  const vertices = vertexTimes(samples, edgeBelow).map((time) => {
    const lower = lowerAt(time)
    return { time, lower, upper: lower + valueAt(samples, time) }
  })
  return { gap: false, vertices }
}

function vertexTimes(samples: TimeValuePoint[], edgeBelow: TimeValuePoint[]): number[] {
  const firstSampleTime = samples[0]!.time
  const lastSampleTime = samples[samples.length - 1]!.time
  const bendsBelow = edgeBelow.filter(
    (point) => point.time > firstSampleTime && point.time < lastSampleTime
  )
  const times = new Set([...samples, ...bendsBelow].map((point) => point.time))
  return [...times].sort((earlier, later) => earlier - later)
}

function upperEdgeOf(column: StackedColumn): TimeValuePoint[] {
  return column.vertices.map((vertex) => ({ time: vertex.time, value: vertex.upper }))
}

export function drawStackedBand(
  ctx: CanvasRenderingContext2D,
  series: AreaSeries,
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  color: string,
  style: { fillOpacity?: number | undefined; strokeWidth?: number | undefined } = {}
): void {
  const fillOpacity = style.fillOpacity ?? 0.45
  const strokeWidth = style.strokeWidth ?? 1
  const pixelX = (vertex: StackedVertex): number => xScale(new Date(vertex.time * 1000))

  for (const run of contiguousRuns(series.columns)) {
    const vertices = run.flatMap((column) => column.vertices)
    ctx.beginPath()
    vertices.forEach((vertex, index) => {
      if (index === 0) {
        ctx.moveTo(pixelX(vertex), yScale(vertex.upper))
      } else {
        ctx.lineTo(pixelX(vertex), yScale(vertex.upper))
      }
    })
    for (const vertex of [...vertices].reverse()) {
      ctx.lineTo(pixelX(vertex), yScale(vertex.lower))
    }
    ctx.closePath()
    ctx.fillStyle = colorWithAlpha(color, fillOpacity)
    ctx.fill()
    ctx.strokeStyle = color
    ctx.lineWidth = strokeWidth
    ctx.stroke()
  }
}

function contiguousRuns(columns: StackedColumn[]): StackedColumn[][] {
  const runs: StackedColumn[][] = []
  let run: StackedColumn[] = []
  for (const column of columns) {
    if (column.gap) {
      if (run.length > 0) {
        runs.push(run)
      }
      run = []
    } else {
      run.push(column)
    }
  }
  if (run.length > 0) {
    runs.push(run)
  }
  return runs
}

function colorWithAlpha(color: string, alpha: number): string {
  const red = parseInt(color.slice(1, 3), 16)
  const green = parseInt(color.slice(3, 5), 16)
  const blue = parseInt(color.slice(5, 7), 16)
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`
}
