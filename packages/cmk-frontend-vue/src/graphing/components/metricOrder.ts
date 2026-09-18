/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Metric } from './TimeSeriesGraph'

/**
 * The metrics as they read down the graph: lines above the areas they overlay, a stack's top
 * layer first, the mirrored lower half below the upward one. Legend and tooltip both list in
 * this order. The input is the draw order, which stacks bottom-up.
 */
export function orderMetricsTopToBottom(metrics: Metric[]): Metric[] {
  const drawn = metrics.filter((metric) => !isStackReference(metric))
  const upwardDrawnBottomUp = drawn.filter((metric) => !metric.render.inverse)
  const mirroredDrawnTopDown = drawn.filter((metric) => metric.render.inverse)
  return [
    ...topmostFirst(upwardDrawnBottomUp.filter(isLine)),
    ...topmostFirst(upwardDrawnBottomUp.filter(isArea)),
    ...mirroredDrawnTopDown.filter(isArea),
    ...mirroredDrawnTopDown.filter(isLine),
    ...metrics.filter(isStackReference)
  ]
}

function isLine(metric: Metric): boolean {
  return metric.render.stack === null
}

function isArea(metric: Metric): boolean {
  return metric.render.stack !== null
}

/** Hidden members carry the baseline a stack is drawn from, not a series of their own. */
function isStackReference(metric: Metric): boolean {
  return metric.render.hidden
}

function topmostFirst(seriesInDrawOrder: Metric[]): Metric[] {
  return [...seriesInDrawOrder].reverse()
}
