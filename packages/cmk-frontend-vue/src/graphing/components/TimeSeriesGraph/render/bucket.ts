/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { M4Bucket } from '../decimation/types'
import type { ConsolidationFn } from '../types'

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
