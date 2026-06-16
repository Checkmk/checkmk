/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { downsampleToColumns, m4 } from '@/graphing/components/TimeSeriesGraph/decimation/decimate'
import type { M4Bucket } from '@/graphing/components/TimeSeriesGraph/decimation/types'

function makeBucket(
  startTime: number,
  endTime: number,
  values: { min: number; max: number; first: number; last: number }
): M4Bucket {
  return {
    startTime,
    endTime,
    gap: false,
    minValue: values.min,
    maxValue: values.max,
    minValueTime: startTime,
    maxValueTime: endTime,
    firstValue: values.first,
    firstValueTime: startTime,
    lastValue: values.last,
    lastValueTime: endTime,
    sampleCount: 1,
    valueSum: values.first
  }
}

describe('m4', () => {
  test('reduces N samples into bucketCount buckets', () => {
    const timeRange = { start: 0, end: 2, step: 1 }

    const oneBucket = m4([10, 20], timeRange, 1)
    const twoBuckets = m4([10, 20], timeRange, 2)

    expect(oneBucket.length).toBe(1)
    expect(twoBuckets.length).toBe(2)
  })

  test('keeps the min and max within a bucket', () => {
    const timeRange = { start: 0, end: 3, step: 1 }

    const [bucket] = m4([1, 99, 2], timeRange, 1)

    expect(bucket!.minValue).toBe(1)
    expect(bucket!.maxValue).toBe(99)
  })

  test('keeps the first and last sample of a bucket', () => {
    const timeRange = { start: 0, end: 3, step: 1 }

    const [bucket] = m4([1, 99, 2], timeRange, 1)

    expect(bucket!.firstValue).toBe(1)
    expect(bucket!.lastValue).toBe(2)
  })

  test('counts only finite samples', () => {
    const timeRange = { start: 0, end: 3, step: 1 }

    const [bucket] = m4([1, NaN, 3], timeRange, 1)

    expect(bucket!.sampleCount).toBe(2)
  })

  test('flags a bucket with no finite sample as a gap', () => {
    const timeRange = { start: 0, end: 2, step: 1 }

    const buckets = m4([10, null], timeRange, 2)

    expect(buckets[1]!.gap).toBe(true)
  })

  test('returns an empty array for null, empty, or non-positive bucketCount', () => {
    const timeRange = { start: 0, end: 2, step: 1 }

    expect(m4(null, timeRange, 4)).toEqual([])
    expect(m4([], timeRange, 4)).toEqual([])
    expect(m4([10, 20], timeRange, 0)).toEqual([])
  })
})

describe('downsampleToColumns', () => {
  test('reduces a cache to the requested column count', () => {
    const cache = [
      makeBucket(0, 10, { min: 1, max: 5, first: 3, last: 4 }),
      makeBucket(10, 20, { min: 0, max: 9, first: 6, last: 8 })
    ]

    const columns = downsampleToColumns(cache, [0, 20], 1)

    expect(columns.length).toBe(1)
  })

  test('keeps the global min and max across the merge', () => {
    const cache = [
      makeBucket(0, 10, { min: 1, max: 5, first: 3, last: 4 }),
      makeBucket(10, 20, { min: 0, max: 9, first: 6, last: 8 })
    ]

    const [column] = downsampleToColumns(cache, [0, 20], 1)

    expect(column!.minValue).toBe(0)
    expect(column!.maxValue).toBe(9)
  })

  test('keeps the outer first and last across the merge', () => {
    const cache = [
      makeBucket(0, 10, { min: 1, max: 5, first: 3, last: 4 }),
      makeBucket(10, 20, { min: 0, max: 9, first: 6, last: 8 })
    ]

    const [column] = downsampleToColumns(cache, [0, 20], 1)

    expect(column!.firstValue).toBe(3)
    expect(column!.lastValue).toBe(8)
  })

  test('scopes columns to a zoomed sub-range', () => {
    const cache = [
      makeBucket(0, 100, { min: 1, max: 2, first: 1, last: 2 }),
      makeBucket(100, 200, { min: 3, max: 4, first: 3, last: 4 }),
      makeBucket(200, 300, { min: 5, max: 6, first: 5, last: 6 }),
      makeBucket(300, 400, { min: 7, max: 8, first: 7, last: 8 })
    ]

    const columns = downsampleToColumns(cache, [200, 400], 2)

    expect(columns[0]!.startTime).toBe(200)
    expect(columns.at(-1)!.endTime).toBe(400)
  })

  test('marks a column with no contributing buckets as a gap', () => {
    const cache = [makeBucket(0, 10, { min: 1, max: 2, first: 1, last: 2 })]

    const columns = downsampleToColumns(cache, [0, 20], 2)

    expect(columns[0]!.gap).toBe(false)
    expect(columns[1]!.gap).toBe(true)
  })

  test('returns an empty array for empty cache, non-positive columns, or non-positive span', () => {
    const cache = [makeBucket(0, 10, { min: 1, max: 2, first: 1, last: 2 })]

    expect(downsampleToColumns([], [0, 20], 2)).toEqual([])
    expect(downsampleToColumns(cache, [0, 20], 0)).toEqual([])
    expect(downsampleToColumns(cache, [20, 20], 2)).toEqual([])
  })
})

describe('m4 + downsampleToColumns', () => {
  test('preserves the global min and max through two-stage reduction', () => {
    const timeRange = { start: 0, end: 8, step: 1 }
    const raw = [5, 1, 9, 3, 7, 0, 8, 2]

    const twoStage = downsampleToColumns(m4(raw, timeRange, 8), [0, 8], 2)

    expect(Math.min(twoStage[0]!.minValue, twoStage[1]!.minValue)).toBe(0)
    expect(Math.max(twoStage[0]!.maxValue, twoStage[1]!.maxValue)).toBe(9)
  })
})
