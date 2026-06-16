/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { timestampAt } from '../axes/timeAxis'
import type { TimeRange } from '../types'
import type { M4Bucket, M4Cache } from './types'

interface BucketAccumulator {
  minValue: number
  maxValue: number
  minValueTime: number
  maxValueTime: number
  firstValue: number
  firstValueTime: number
  lastValue: number
  lastValueTime: number
  sampleCount: number
  valueSum: number
}

function newBucketAccumulator(): BucketAccumulator {
  return {
    minValue: Infinity,
    maxValue: -Infinity,
    minValueTime: NaN,
    maxValueTime: NaN,
    firstValue: NaN,
    firstValueTime: NaN,
    lastValue: NaN,
    lastValueTime: NaN,
    sampleCount: 0,
    valueSum: 0
  }
}

function assembleBucket(startTime: number, endTime: number, acc: BucketAccumulator): M4Bucket {
  return {
    startTime,
    endTime,
    gap: acc.sampleCount === 0,
    minValue: acc.sampleCount ? acc.minValue : NaN,
    maxValue: acc.sampleCount ? acc.maxValue : NaN,
    minValueTime: acc.minValueTime,
    maxValueTime: acc.maxValueTime,
    firstValue: acc.firstValue,
    firstValueTime: acc.firstValueTime,
    lastValue: acc.lastValue,
    lastValueTime: acc.lastValueTime,
    sampleCount: acc.sampleCount,
    valueSum: acc.valueSum
  }
}

export function m4(
  values: (number | null)[] | null,
  timeRange: TimeRange,
  bucketCount: number
): M4Cache {
  if (!values || values.length === 0 || bucketCount <= 0) {
    return []
  }
  const total = values.length
  const buckets: M4Bucket[] = new Array(bucketCount)
  for (let i = 0; i < bucketCount; i++) {
    const lo = Math.floor((i * total) / bucketCount)
    const hi = Math.floor(((i + 1) * total) / bucketCount)
    const acc = newBucketAccumulator()
    for (let j = lo; j < hi; j++) {
      const value = values[j]
      if (value === null || value === undefined || !Number.isFinite(value)) {
        continue
      }
      const timestamp = timestampAt(timeRange, j)
      if (acc.sampleCount === 0) {
        acc.firstValue = value
        acc.firstValueTime = timestamp
      }
      acc.lastValue = value
      acc.lastValueTime = timestamp
      if (value < acc.minValue) {
        acc.minValue = value
        acc.minValueTime = timestamp
      }
      if (value > acc.maxValue) {
        acc.maxValue = value
        acc.maxValueTime = timestamp
      }
      acc.valueSum += value
      acc.sampleCount++
    }
    buckets[i] = assembleBucket(timestampAt(timeRange, lo), timestampAt(timeRange, hi), acc)
  }
  return buckets
}

export function downsampleToColumns(
  cache: M4Cache,
  range: [number, number],
  columns: number
): M4Cache {
  if (cache.length === 0 || columns <= 0) {
    return []
  }
  const [rangeStart, rangeEnd] = range
  const span = rangeEnd - rangeStart
  if (span <= 0) {
    return []
  }

  const out: M4Bucket[] = new Array(columns)
  let consumedIndex = 0
  while (consumedIndex < cache.length && cache[consumedIndex]!.endTime <= rangeStart) {
    consumedIndex++
  }

  for (let i = 0; i < columns; i++) {
    const cStart = rangeStart + (i * span) / columns
    const cEnd = rangeStart + ((i + 1) * span) / columns
    const acc = newBucketAccumulator()

    let scanIndex = consumedIndex
    while (scanIndex < cache.length && cache[scanIndex]!.startTime < cEnd) {
      const bucket = cache[scanIndex]!
      if (!bucket.gap && bucket.endTime > cStart) {
        if (acc.sampleCount === 0) {
          acc.firstValue = bucket.firstValue
          acc.firstValueTime = bucket.firstValueTime
        }
        acc.lastValue = bucket.lastValue
        acc.lastValueTime = bucket.lastValueTime
        if (bucket.minValue < acc.minValue) {
          acc.minValue = bucket.minValue
          acc.minValueTime = bucket.minValueTime
        }
        if (bucket.maxValue > acc.maxValue) {
          acc.maxValue = bucket.maxValue
          acc.maxValueTime = bucket.maxValueTime
        }
        acc.sampleCount += bucket.sampleCount
        acc.valueSum += bucket.valueSum
      }
      scanIndex++
    }
    while (consumedIndex < cache.length && cache[consumedIndex]!.endTime <= cEnd) {
      consumedIndex++
    }

    out[i] = assembleBucket(cStart, cEnd, acc)
  }
  return out
}
