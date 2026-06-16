/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ScaleLinear, type ScaleTime, scaleLinear, scaleTime } from 'd3-scale'

import type { TimeRange } from './types'

export function buildXScale(timeRange: TimeRange, plotWidth: number): ScaleTime<number, number> {
  return scaleTime()
    .domain([new Date(timeRange.start * 1000), new Date(timeRange.end * 1000)])
    .range([0, plotWidth])
}

export function buildYScale(
  domain: [number, number],
  plotHeight: number,
  padding: number
): ScaleLinear<number, number> {
  return scaleLinear()
    .domain(domain)
    .range([plotHeight - padding, padding])
}
