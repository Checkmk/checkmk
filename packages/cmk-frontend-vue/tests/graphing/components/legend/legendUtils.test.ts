/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import type { HorizontalLine, Metric } from '@/graphing/components/TimeSeriesGraph'
import { horizontalLineValue, metricStats } from '@/graphing/components/legend/legendUtils'

const UNIT: Metric['metadata']['unit'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

const SI_BYTES: Metric['metadata']['unit'] = {
  notation: 'si',
  symbol: 'B',
  precision: { type: 'auto', digits: 2 },
  convertible: false
}

/** What "Settings > Unit > Custom > Notation: IEC" enforces on a byte graph. */
const IEC_BYTES: Metric['metadata']['unit'] = {
  notation: 'iec',
  symbol: 'B',
  precision: { type: 'auto', digits: 2 },
  convertible: false
}

/** Reads '33.55 MB' in SI, '32 MiB' in IEC. */
const MEBIBYTES_32 = 33_554_432

function makeByteMetric(): Metric {
  const metric = makeMetric([MEBIBYTES_32])
  return { ...metric, metadata: { ...metric.metadata, unit: SI_BYTES } }
}

function makeMetric(dataPoints: (number | null)[]): Metric {
  return {
    metadata: { name: 'util', title: 'Utilization', unit: UNIT, color: '#ff0000', attributes: [] },
    render: { stack: null, inverse: false, hidden: false },
    data_points: dataPoints
  }
}

function renderedAlone(value: number): string {
  return metricStats(makeMetric([value])).last
}

test('last reports the final sample of a series ending in a value', () => {
  const finalSample = 2

  const stats = metricStats(makeMetric([3, 1, finalSample]))

  expect(stats.last).toBe(renderedAlone(finalSample))
})

test('last reports the final present sample of a series ending in a gap', () => {
  const finalSample = 2

  const stats = metricStats(makeMetric([3, 1, finalSample, null]))

  expect(stats.last).toBe(renderedAlone(finalSample))
})

test('stats tell apart two values one axis step apart', () => {
  const valueResolution = 0.005

  const stats = metricStats(makeMetric([0.195, 0.2]), valueResolution)

  expect([stats.min, stats.max]).toEqual(['0.195', '0.2'])
})

test('stats fall back to the unit precision without an axis resolution', () => {
  const stats = metricStats(makeMetric([0.195]))

  expect(stats.last).toBe('0.2')
})

test('stats render in the axis unit, so the legend cannot contradict the axis', () => {
  const stats = metricStats(makeByteMetric(), null, IEC_BYTES)

  expect(stats.last).toBe('32 MiB')
})

test('stats render in the metric unit when the graph names no axis unit', () => {
  const stats = metricStats(makeByteMetric(), null, null)

  expect(stats.last).toBe('33.55 MB')
})

test('a horizontal line renders in the axis unit', () => {
  expect(horizontalLineValue(makeByteLine(), null, IEC_BYTES)).toBe('32 MiB')
})

test('a horizontal line renders in its own unit when the graph names no axis unit', () => {
  expect(horizontalLineValue(makeByteLine(), null, null)).toBe('33.55 MB')
})

function makeByteLine(): HorizontalLine {
  return {
    name: 'scalar_of(warning,rrd_metric(h/svc/mem_used))',
    title: 'Warning',
    value: MEBIBYTES_32,
    unit: SI_BYTES,
    color: '#ffaa00'
  }
}
