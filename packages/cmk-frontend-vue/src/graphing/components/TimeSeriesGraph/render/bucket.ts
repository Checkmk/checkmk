/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConsolidationFn } from '../../consolidation'
import type { M4Bucket } from '../decimation/types'

// The time a bucket is drawn at: the midpoint of the samples it holds, not the centre of the
// column it occupies. A sample wider than one column stays a single point that way, so the
// curve connects sample-to-sample instead of stepping across the columns the sample covers.
export function bucketAnchorTime(bucket: M4Bucket): number {
  return bucket.gap ? NaN : (bucket.firstValueTime + bucket.lastValueTime) / 2
}

// Where a consolidated value belongs on the time axis: `min`/`max` are single samples with a
// time of their own, an average is no sample and keeps the anchor. See `useHover.drawnTime`.
export function consolidatedSampleTime(bucket: M4Bucket, consolidation: ConsolidationFn): number {
  if (bucket.gap || bucket.sampleCount === 0) {
    return NaN
  }
  switch (consolidation) {
    case 'min':
      return bucket.minValueTime
    case 'max':
      return bucket.maxValueTime
    case 'avg':
      return bucketAnchorTime(bucket)
  }
}

export function selectConsolidatedValue(bucket: M4Bucket, consolidation: ConsolidationFn): number {
  if (bucket.gap || bucket.sampleCount === 0) {
    return NaN
  }
  switch (consolidation) {
    case 'min':
      return bucket.minValue
    case 'max':
      return bucket.maxValue
    case 'avg':
      return bucket.valueSum / bucket.sampleCount
  }
}

export function invertBucket(bucket: M4Bucket): M4Bucket {
  if (bucket.gap) {
    return bucket
  }
  return {
    ...bucket,
    minValue: -bucket.maxValue,
    minValueTime: bucket.maxValueTime,
    maxValue: -bucket.minValue,
    maxValueTime: bucket.minValueTime,
    firstValue: -bucket.firstValue,
    lastValue: -bucket.lastValue,
    valueSum: -bucket.valueSum
  }
}
