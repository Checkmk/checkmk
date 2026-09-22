/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MetricUnitMap, ObjectState, ShapeElement } from '@/maps/types/api'
import { renderMetricValue } from '@/maps/utils/metricFormat'
import {
  getMetric,
  hasPercentScale,
  parsePerfData,
  utilColor,
  utilPercent
} from '@/maps/utils/perf'
import { stateColor } from '@/maps/utils/stateColors'

import { hasBinding } from './binding'

export interface FlowVisual {
  /** Stroke colour: utilisation gradient when flow + metric, else state, else manual. */
  color: string
  /** Stroke width in slide px (grows with utilisation when flowing). */
  width: number
  /** Dash pattern for marching-ants flow, or the shape's static dash. */
  dashArray: string | undefined
  /** Seconds per flow cycle (lower = busier link); null = no animation. */
  durationSec: number | null
  /** 0–100 utilisation, or null when no percentage-scaled metric is bound. */
  util: number | null
  /** Short label for the midpoint pill (util %, raw value, or state). */
  valueText: string
}

// A connector's value pill defaults to VISIBLE (label === null shows the live
// value); only an explicit ``show: false`` hides it. Box shapes default the
// other way (see PresentationElementView.shapeLabelShow).
export function connectorLabelVisible(el: ShapeElement): boolean {
  return el.label?.show !== false
}

function staticDash(dash: ShapeElement['dash'], w: number): string | undefined {
  if (dash === 'dashed') {
    return `${w * 3} ${w * 2}`
  }
  if (dash === 'dotted') {
    return `${w} ${w * 1.5}`
  }
  return undefined
}

/** Resolve the visual treatment of a (possibly bound / flowing) line connector
 * from its definition and the live state. Pure so the inline line and the
 * slide-overlay connector render identically. ``metricName`` overrides the
 * element's forward metric — the two-way weathermap resolves each direction
 * with its own metric. */
export function flowVisual(
  el: ShapeElement,
  state: ObjectState | undefined,
  metricName: string | null = el.flow_metric ?? null,
  units: MetricUnitMap = {}
): FlowVisual {
  const bound = hasBinding(el)
  const metrics = parsePerfData(state?.perf_data ?? '')
  const m = metricName ? getMetric(metrics, metricName) : null
  const util = m && hasPercentScale(m) ? utilPercent(m) : null

  let color: string
  if (el.flow && util !== null) {
    color = utilColor(util)
  } else if (bound) {
    color = stateColor(state?.state)
  } else {
    color = el.stroke && el.stroke.length > 0 ? el.stroke : 'var(--pres-shape-stroke)'
  }

  const baseW = el.stroke_width || 3
  const width = el.flow && util !== null ? baseW + (util / 100) * Math.max(baseW, 8) : baseW

  const animated = !!el.flow
  const dashArray = animated
    ? `${Math.max(8, Math.round(baseW * 3))} ${Math.max(6, Math.round(baseW * 2))}`
    : staticDash(el.dash, baseW)
  // Busier links flow faster: util 0 → 1.8s, util 100 → 0.5s; constant 1.4s without a metric.
  const durationSec = animated ? (util !== null ? 1.8 - (util / 100) * 1.3 : 1.4) : null

  let valueText = ''
  if (util !== null) {
    valueText = `${Math.round(util)}%`
  } else if (m) {
    valueText = renderMetricValue(m.value, units[m.label], m.unit)
  } else if (bound) {
    valueText = state?.state ?? ''
  }

  return { color, width, dashArray, durationSec, util, valueText }
}
