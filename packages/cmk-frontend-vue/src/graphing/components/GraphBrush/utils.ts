/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromAbsolute, getLocalTimeZone } from '@internationalized/date'

import { isoDate, pad2 } from '@/graphing/utils/timeFormat'

import type { Metric } from '../TimeSeriesGraph'

const zonedTime = (unixSeconds: number, timeZone: string) =>
  fromAbsolute(unixSeconds * 1000, timeZone)
const fmtDate = (unixSeconds: number, timeZone: string) => isoDate(zonedTime(unixSeconds, timeZone))
const fmtTime = (unixSeconds: number, timeZone: string) => {
  const zoned = zonedTime(unixSeconds, timeZone)
  return `${pad2(zoned.hour)}:${pad2(zoned.minute)}`
}

export function formatOverviewExtent(
  domain: { start: number; end: number },
  timeZone: string = getLocalTimeZone()
): string {
  const { start, end } = domain
  if (fmtDate(start, timeZone) === fmtDate(end, timeZone)) {
    return `${fmtDate(start, timeZone)} ${fmtTime(start, timeZone)}–${fmtTime(end, timeZone)}`
  }
  return `${fmtDate(start, timeZone)} — ${fmtDate(end, timeZone)}`
}

export interface WindowPreview {
  date: string
  time: string
}

export function formatWindowPreview(
  window: { start: number; end: number },
  timeZone: string = getLocalTimeZone()
): WindowPreview {
  const startDate = fmtDate(window.start, timeZone)
  const endDate = fmtDate(window.end, timeZone)
  return {
    date: startDate === endDate ? startDate : `${startDate} — ${endDate}`,
    time: `${fmtTime(window.start, timeZone)}–${fmtTime(window.end, timeZone)}`
  }
}

export interface SparklineBand {
  lower: number[]
  upper: number[]
  color: string
}

export interface SparklineBands {
  bands: SparklineBand[]
  sampleCount: number
  yMin: number
  yMax: number
}

// Coarse sparkline composition that mirrors the graph renderer's
export function computeSparklineBands(metrics: Metric[]): SparklineBands {
  const sampleCount = (metrics[0]?.data_points ?? []).length
  if (sampleCount === 0) {
    return { bands: [], sampleCount: 0, yMin: 0, yMax: 0 }
  }
  const groupSums = new Map<string, number[]>()
  let domainMin = 0
  let domainMax = 0
  const bands: SparklineBand[] = []
  for (const metric of metrics) {
    const raw = metric.data_points ?? []
    const sign = metric.render.inverse ? -1 : 1
    const lower = new Array<number>(sampleCount)
    const upper = new Array<number>(sampleCount)
    const stack = metric.render.stack
    const groupSum =
      stack === null ? null : (groupSums.get(stack) ?? new Array<number>(sampleCount).fill(0))
    // Hidden metrics (stack references) advance the stack base but draw no band of their
    // own and do not widen the value domain.
    const hidden = metric.render.hidden
    for (let i = 0; i < sampleCount; i++) {
      const base = groupSum ? groupSum[i]! : 0
      lower[i] = base
      upper[i] = base + sign * (raw[i] ?? 0)
      if (groupSum) {
        groupSum[i] = upper[i]!
      }
      if (!hidden) {
        domainMin = Math.min(domainMin, lower[i]!, upper[i]!)
        domainMax = Math.max(domainMax, lower[i]!, upper[i]!)
      }
    }
    if (stack !== null && groupSum) {
      groupSums.set(stack, groupSum)
    }
    if (!hidden) {
      bands.push({ lower, upper, color: metric.metadata.color })
    }
  }

  const anyInverse = metrics.some((metric) => !metric.render.hidden && metric.render.inverse)
  let yMin = domainMin
  let yMax = domainMax
  if (anyInverse) {
    const extent = Math.max(Math.abs(domainMin), Math.abs(domainMax), 1)
    yMin = -extent
    yMax = extent
  }

  return { bands, sampleCount, yMin, yMax }
}
