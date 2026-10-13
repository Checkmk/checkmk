/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import type { M4Bucket } from '@/graphing/components/TimeSeriesGraph/decimation/types'
import {
  bucketAnchorTime,
  consolidatedSampleTime,
  invertBucket,
  keptSamples,
  selectConsolidatedValue
} from '@/graphing/components/TimeSeriesGraph/render/bucket'

function makeBucket(overrides: Partial<M4Bucket> = {}): M4Bucket {
  return {
    startTime: 0,
    endTime: 10,
    gap: false,
    minValue: 1,
    maxValue: 9,
    minValueTime: 1,
    maxValueTime: 9,
    firstValue: 1,
    firstValueTime: 0,
    lastValue: 9,
    lastValueTime: 9,
    sampleCount: 4,
    valueSum: 16,
    ...overrides
  }
}

describe('selectConsolidatedValue', () => {
  test('min returns the bucket minimum', () => {
    const bucket = makeBucket()

    expect(selectConsolidatedValue(bucket, 'min')).toBe(1)
  })

  test('max returns the bucket maximum', () => {
    const bucket = makeBucket()

    expect(selectConsolidatedValue(bucket, 'max')).toBe(9)
  })

  test('avg returns valueSum divided by sampleCount', () => {
    const bucket = makeBucket()

    expect(selectConsolidatedValue(bucket, 'avg')).toBe(4)
  })

  test('returns NaN for a gap bucket regardless of the consolidation', () => {
    const gapBucket = makeBucket({
      gap: true,
      minValue: NaN,
      maxValue: NaN,
      sampleCount: 0,
      valueSum: 0
    })

    expect(Number.isNaN(selectConsolidatedValue(gapBucket, 'avg'))).toBe(true)
  })

  test('returns NaN when the bucket holds no samples', () => {
    const emptyBucket = makeBucket({ sampleCount: 0, valueSum: 0 })

    expect(Number.isNaN(selectConsolidatedValue(emptyBucket, 'avg'))).toBe(true)
  })
})

describe('bucketAnchorTime', () => {
  test('is the midpoint of the samples, not of the column', () => {
    const bucket = makeBucket({ startTime: 0, endTime: 100, firstValueTime: 10, lastValueTime: 30 })

    expect(bucketAnchorTime(bucket)).toBe(20)
  })

  test('is NaN for a gap bucket, which has no drawn point', () => {
    const gapBucket = makeBucket({ gap: true })

    expect(Number.isNaN(bucketAnchorTime(gapBucket))).toBe(true)
  })
})

describe('keptSamples', () => {
  test('lists the first, the extremes and the last sample in time order', () => {
    const bucket = makeBucket({
      firstValueTime: 0,
      firstValue: 3,
      maxValueTime: 2,
      maxValue: 9,
      minValueTime: 5,
      minValue: 1,
      lastValueTime: 9,
      lastValue: 4
    })

    const samples = keptSamples(bucket)

    expect(samples).toEqual([
      { time: bucket.firstValueTime, value: bucket.firstValue },
      { time: bucket.maxValueTime, value: bucket.maxValue },
      { time: bucket.minValueTime, value: bucket.minValue },
      { time: bucket.lastValueTime, value: bucket.lastValue }
    ])
  })

  test('a sample that is both an extreme and the last is listed once', () => {
    const bucket = makeBucket({ maxValueTime: 9, maxValue: 9, lastValueTime: 9, lastValue: 9 })

    const samples = keptSamples(bucket)

    expect(samples.filter((sample) => sample.time === bucket.lastValueTime)).toHaveLength(1)
  })

  test('a gap bucket keeps no samples', () => {
    const gapBucket = makeBucket({ gap: true })

    expect(keptSamples(gapBucket)).toEqual([])
  })
})

describe('consolidatedSampleTime', () => {
  test('min and max are reported at the time their sample was taken', () => {
    const bucket = makeBucket({ minValueTime: 3, maxValueTime: 7 })

    expect(consolidatedSampleTime(bucket, 'min')).toBe(3)
    expect(consolidatedSampleTime(bucket, 'max')).toBe(7)
  })

  test('avg belongs to no sample and keeps the anchor', () => {
    const bucket = makeBucket({ firstValueTime: 10, lastValueTime: 30 })

    expect(consolidatedSampleTime(bucket, 'avg')).toBe(20)
  })

  test('is NaN for a gap bucket, which has no drawn point', () => {
    const gapBucket = makeBucket({ gap: true })

    expect(Number.isNaN(consolidatedSampleTime(gapBucket, 'max'))).toBe(true)
  })
})

describe('invertBucket', () => {
  test('negates the value fields and swaps the min/max roles', () => {
    const bucket: M4Bucket = {
      startTime: 0,
      endTime: 10,
      gap: false,
      minValue: 1,
      maxValue: 9,
      minValueTime: 1,
      maxValueTime: 9,
      firstValue: 1,
      firstValueTime: 0,
      lastValue: 9,
      lastValueTime: 9,
      sampleCount: 4,
      valueSum: 16
    }

    const inverted = invertBucket(bucket)

    expect(inverted.minValue).toBe(-9) // formerly the maximum
    expect(inverted.maxValue).toBe(-1) // formerly the minimum
    expect(inverted.minValueTime).toBe(9) // timestamp of the formerly-max sample
    expect(inverted.maxValueTime).toBe(1) // timestamp of the formerly-min sample
    expect(inverted.firstValue).toBe(-1)
    expect(inverted.lastValue).toBe(-9)
    expect(inverted.valueSum).toBe(-16)
  })

  test('passes gap buckets through unchanged', () => {
    const gapBucket = makeBucket({ gap: true, minValue: NaN, maxValue: NaN })

    expect(invertBucket(gapBucket)).toEqual(gapBucket)
  })
})
