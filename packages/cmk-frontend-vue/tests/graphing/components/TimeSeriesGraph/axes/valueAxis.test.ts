/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { computeYDomain } from '@/graphing/components/TimeSeriesGraph/axes/valueAxis'

function bucket(minValue: number, maxValue: number, gap = false) {
  return { gap, minValue, maxValue }
}

describe('computeYDomain', () => {
  test('spans the min and max across all metric buckets', () => {
    const metrics = [[bucket(2, 5)], [bucket(-1, 3)]]

    const domain = computeYDomain(metrics)

    expect(domain).toEqual([-1, 5])
  })

  test('skips gap buckets', () => {
    const metrics = [[bucket(1, 5), bucket(-100, 100, true)]]

    const domain = computeYDomain(metrics)

    expect(domain).toEqual([1, 5])
  })

  test('returns [0, 1] when no finite buckets exist', () => {
    const allGap = [[bucket(-100, 100, true)]]

    expect(computeYDomain([])).toEqual([0, 1])
    expect(computeYDomain(allGap)).toEqual([0, 1])
  })

  test('pads a flat domain', () => {
    const metrics = [[bucket(5, 5)]]

    const domain = computeYDomain(metrics)

    expect(domain).toEqual([4.5, 5.5])
  })

  test('forces a symmetric domain around zero when flagged', () => {
    const metrics = [[bucket(-2, 8)]]

    const domain = computeYDomain(metrics, { symmetric: true })

    expect(domain).toEqual([-8, 8])
  })

  test('guards the all-zero symmetric case', () => {
    const metrics = [[bucket(0, 0)]]

    const domain = computeYDomain(metrics, { symmetric: true })

    expect(domain).toEqual([-0.5, 0.5])
  })
})
