/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Label, NotationFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'
import { axisLeft } from 'd3-axis'
import type { ScaleLinear, ScaleTime } from 'd3-scale'
import type { Selection } from 'd3-selection'
import { select } from 'd3-selection'
import 'd3-transition'
import type { Transition } from 'd3-transition'
import type { Ref } from 'vue'
import { ref } from 'vue'

import { type ValueRangeMode, stepIncrements, valueDomain } from './axes/tickStepping'
import type { TimeAxisTick } from './axes/timeAxis'

// Minimum pixel gap between ticks when computing how many to display.
const MIN_VALUE_TICK_SPACING_PX = 65

// Minimum pixel gap per tick used when computing the domain step via valueDomain.
// Smaller than MIN_VALUE_TICK_SPACING_PX because domain computation requests more ticks
// than are ultimately displayed.
const VALUE_DOMAIN_ALIGNMENT_PX = 50

// Vertical offset of an x-axis label's baseline below the plot bottom edge.
const TIME_LABEL_BASELINE_OFFSET_PX = 14

// Headroom above the domain maximum so a curve touching it is not clipped. The bottom gets none:
// the domain minimum has to land on the x-axis, or an area filled down to zero floats above it.
const VALUE_AXIS_TOP_PADDING_PX = 4

export const AXIS_CLASSES = {
  valueGrid: 'graphing-time-series-graph__grid-y',
  valueAxis: 'graphing-time-series-graph__y-axis',
  timeGridLines: 'graphing-time-series-graph__x-grid',
  timeBaseline: 'graphing-time-series-graph__x-baseline',
  timeLabels: 'graphing-time-series-graph__x-labels'
} as const

type GroupSelection = Selection<SVGGElement, null, SVGGElement, unknown>
type GroupTransition = Transition<SVGGElement, null, SVGGElement, unknown>

export interface AxisLabelVisibility {
  showLabels: boolean
}

interface ValueLabel {
  position: number
  text: string
}

function asValueLabels(labels: Label[]): ValueLabel[] {
  return labels.map((label) => ({ position: label.value, text: label.text }))
}

// Labels must land where the unit considers round, which d3's decimal-only ticks cannot do: an IEC
// axis steps in powers of two, so a 2 * 10^6 byte step reads as "1.91 MiB" and contradicts the
// legend. renderYLabels takes one sign at a time, hence the split below.
function computeValueLabels(
  formatter: NotationFormatter,
  domainMin: number,
  domainMax: number,
  targetCount: number
): ValueLabel[] {
  if (targetCount <= 0) {
    return []
  }
  if (domainMin >= 0) {
    return asValueLabels(
      formatter.renderYLabels({ kind: 'positive', start: domainMin, end: domainMax }, targetCount)
    )
  }
  if (domainMax <= 0) {
    return asValueLabels(
      formatter.renderYLabels({ kind: 'negative', start: domainMin, end: domainMax }, targetCount)
    )
  }
  // Split as _compute_labels_from_api does in cmk/gui/graphing/_artwork.py: each side sized by its
  // share of the domain, and the negative half's zero dropped because the positive half carries one.
  const negativeShare = -domainMin / (domainMax - domainMin)
  const negative = formatter.renderYLabels(
    { kind: 'negative', start: domainMin, end: 0 },
    Math.max(1, Math.round(targetCount * negativeShare))
  )
  const positive = formatter.renderYLabels(
    { kind: 'positive', start: 0, end: domainMax },
    Math.max(1, Math.round(targetCount * (1 - negativeShare)))
  )
  return [...asValueLabels(negative.slice(1)), ...asValueLabels(positive)]
}

/** Halve the gap between neighbouring labels, for the grid's unlabelled intermediate lines. */
function withMidpoints(positions: number[]): number[] {
  const ascending = [...positions].sort((first, second) => first - second)
  return ascending.flatMap((position, index) =>
    index === 0 ? [position] : [(ascending[index - 1]! + position) / 2, position]
  )
}

export function useAxes(
  axisGroupRef: Ref<SVGGElement | null>,
  xScale: ScaleTime<number, number>,
  yScale: ScaleLinear<number, number>,
  plotWidth: Ref<number>,
  plotHeight: Ref<number>,
  yStepping: Ref<'binary' | 'decimal'>,
  yFormatter: Ref<NotationFormatter | null>
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

  function prepareValueDomain(
    rawYMin: number,
    rawYMax: number,
    mode: ValueRangeMode = 'aligned'
  ): void {
    const tickCount = Math.max(2, Math.ceil(plotHeight.value / VALUE_DOMAIN_ALIGNMENT_PX))
    const increments = stepIncrements(yStepping.value)
    const [alignedMin, alignedMax, step] = valueDomain(
      [rawYMin, rawYMax],
      tickCount,
      increments,
      mode
    )
    yScale.domain([alignedMin, alignedMax])
    yScale.range([plotHeight.value, VALUE_AXIS_TOP_PADDING_PX])
    yStep.value = step
  }

  function valueLabels(): ValueLabel[] {
    const [domainMin, domainMax] = yScale.domain() as [number, number]
    const tickCount = yTickCount()
    const formatter = yFormatter.value
    const unitLabels = formatter
      ? computeValueLabels(formatter, domainMin, domainMax, tickCount)
      : []
    if (unitLabels.length > 0) {
      return unitLabels
    }
    return yScale.ticks(tickCount).map((value) => ({ position: value, text: String(value) }))
  }

  function valueTickLabels(): string[] {
    return valueLabels().map((label) => label.text)
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
        .tickValues(withMidpoints(valueLabels().map((label) => label.position)))
        .tickSize(-plotWidth.value)
        .tickFormat(() => '')
    )
  }

  function drawValueAxis({ showLabels }: AxisLabelVisibility): void {
    if (!axisGroupRef.value) {
      return
    }

    const axisGroup = select(axisGroupRef.value)

    const yAxis = axisGroup
      .selectAll<SVGGElement, null>(`g.${AXIS_CLASSES.valueAxis}`)
      .data([null])
      .join('g')
      .classed(AXIS_CLASSES.valueAxis, true)
    const labels = valueLabels()
    const textByPosition = new Map(labels.map((label) => [label.position, label.text]))
    applyTransition(yAxis).call(
      axisLeft(yScale)
        .tickValues(labels.map((label) => label.position))
        .tickFormat(showLabels ? (value) => textByPosition.get(value.valueOf()) ?? '' : () => '')
    )
  }

  function drawTimeAxis(ticks: TimeAxisTick[], { showLabels }: AxisLabelVisibility): void {
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
      .data(showLabels ? ticks.filter((tick) => tick.text !== null) : [])
      .join('text')
      .attr('x', positionToX)
      .attr('y', height + TIME_LABEL_BASELINE_OFFSET_PX)
      .attr('text-anchor', 'middle')
      .text((tick) => tick.text)
  }

  return { prepareValueDomain, valueTickLabels, drawValueGrid, drawValueAxis, drawTimeAxis }
}
