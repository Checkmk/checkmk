/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { axisLeft } from 'd3-axis'
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import type { Selection } from 'd3-selection'
import { select } from 'd3-selection'
import type { Transition } from 'd3-transition'
import 'd3-transition'
import type { Ref } from 'vue'
import { ref } from 'vue'

import { alignedDomain, stepIncrements } from './axes/tickStepping'
import type { TimeAxisTick } from './axes/timeAxis'

// Minimum pixel gap between ticks when computing how many to display.
const MIN_VALUE_TICK_SPACING_PX = 65

// Minimum pixel gap per tick used when computing the domain step via alignedDomain.
// Smaller than MIN_VALUE_TICK_SPACING_PX because domain computation requests more ticks
// than are ultimately displayed.
const VALUE_DOMAIN_ALIGNMENT_PX = 50

// Vertical offset of an x-axis label's baseline below the plot bottom edge.
const TIME_LABEL_BASELINE_OFFSET_PX = 14

export const AXIS_CLASSES = {
  valueGrid: 'graphing-time-series-graph__grid-y',
  valueAxis: 'graphing-time-series-graph__y-axis',
  timeGridLines: 'graphing-time-series-graph__x-grid',
  timeBaseline: 'graphing-time-series-graph__x-baseline',
  timeLabels: 'graphing-time-series-graph__x-labels'
} as const

type GroupSelection = Selection<SVGGElement, null, SVGGElement, unknown>
type GroupTransition = Transition<SVGGElement, null, SVGGElement, unknown>

export function useAxes(
  axisGroupRef: Ref<SVGGElement | null>,
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  plotWidth: Ref<number>,
  plotHeight: Ref<number>,
  yStepping: Ref<'binary' | 'decimal'>,
  yTickFormatter: Ref<(value: number) => string>
) {
  const yStep = ref<number>(1)

  function applyTransition(selection: GroupSelection): GroupTransition {
    return selection.transition().duration(500)
  }

  function yTickCount(): number {
    const [domainMin, domainMax] = yScale.domain() as [number, number]
    return Math.min(
      Math.ceil(plotHeight.value / MIN_VALUE_TICK_SPACING_PX),
      Math.round((domainMax - domainMin) / yStep.value)
    )
  }

  function prepareValueDomain(rawYMin: number, rawYMax: number): void {
    const tickCount = Math.max(2, Math.ceil(plotHeight.value / VALUE_DOMAIN_ALIGNMENT_PX))
    const increments = stepIncrements(yStepping.value)
    const [alignedMin, alignedMax, step] = alignedDomain([rawYMin, rawYMax], tickCount, increments)
    yScale.domain([alignedMin, alignedMax])
    yStep.value = step
  }

  function drawValueGrid(): void {
    if (!axisGroupRef.value) {
      return
    }

    const axisGroup = select(axisGroupRef.value)

    const gridY = axisGroup
      .selectAll<SVGGElement, null>(`g.${AXIS_CLASSES.valueGrid}`)
      .data([null])
      .join('g')
      .classed(AXIS_CLASSES.valueGrid, true)
    applyTransition(gridY).call(
      axisLeft(yScale)
        .ticks(yTickCount() * 2)
        .tickSize(-plotWidth.value)
        .tickFormat(() => '')
    )
  }

  function drawValueAxis(): void {
    if (!axisGroupRef.value) {
      return
    }

    const axisGroup = select(axisGroupRef.value)

    const yAxis = axisGroup
      .selectAll<SVGGElement, null>(`g.${AXIS_CLASSES.valueAxis}`)
      .data([null])
      .join('g')
      .classed(AXIS_CLASSES.valueAxis, true)
    const formatter = yTickFormatter.value
    applyTransition(yAxis).call(
      axisLeft(yScale)
        .ticks(yTickCount())
        .tickFormat((value) => formatter(value.valueOf()))
    )
  }

  function drawTimeAxis(ticks: TimeAxisTick[]): void {
    if (!axisGroupRef.value) {
      return
    }

    const axisGroup = select(axisGroupRef.value)
    const height = plotHeight.value
    const positionToX = (tick: TimeAxisTick): number => xScale(new Date(tick.position * 1000))

    const verticalGridLinesGroup = axisGroup
      .selectAll<SVGGElement, null>(`g.${AXIS_CLASSES.timeGridLines}`)
      .data([null])
      .join('g')
      .classed(AXIS_CLASSES.timeGridLines, true)
    verticalGridLinesGroup
      .selectAll<SVGLineElement, TimeAxisTick>('line')
      .data(ticks.filter((tick) => tick.lineWidth > 0))
      .join('line')
      .attr('x1', positionToX)
      .attr('x2', positionToX)
      .attr('y1', 0)
      .attr('y2', height)

    const horizontalBaselineGroup = axisGroup
      .selectAll<SVGGElement, null>(`g.${AXIS_CLASSES.timeBaseline}`)
      .data([null])
      .join('g')
      .classed(AXIS_CLASSES.timeBaseline, true)
    horizontalBaselineGroup
      .selectAll<SVGLineElement, null>('line')
      .data([null])
      .join('line')
      .attr('x1', 0)
      .attr('x2', plotWidth.value)
      .attr('y1', height)
      .attr('y2', height)

    const timeLabelsGroup = axisGroup
      .selectAll<SVGGElement, null>(`g.${AXIS_CLASSES.timeLabels}`)
      .data([null])
      .join('g')
      .classed(AXIS_CLASSES.timeLabels, true)
    timeLabelsGroup
      .selectAll<SVGTextElement, TimeAxisTick>('text')
      .data(ticks.filter((tick) => tick.text !== null))
      .join('text')
      .attr('x', positionToX)
      .attr('y', height + TIME_LABEL_BASELINE_OFFSET_PX)
      .attr('text-anchor', 'middle')
      .text((tick) => tick.text)
  }

  return { prepareValueDomain, drawValueGrid, drawValueAxis, drawTimeAxis }
}
