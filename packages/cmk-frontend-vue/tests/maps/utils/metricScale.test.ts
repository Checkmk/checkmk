/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  baseUnit,
  fmtValueWithUnit,
  isSingleCharSIPrefix,
  normalizeMetricValue,
  siScaleOf,
  splitMagnitude
} from '@/maps/utils/metricScale'

describe('siScaleOf', () => {
  it('reads the prefix a check plug-in put on the unit', () => {
    expect(siScaleOf('MB')).toBe(1e6)
    expect(siScaleOf('k')).toBe(1e3)
    expect(siScaleOf('B')).toBe(1)
    expect(siScaleOf(undefined)).toBe(1)
  })

  it('leaves a time unit alone: it scales by 60, not by 1000', () => {
    expect(siScaleOf('ms')).toBe(1)
    expect(siScaleOf('min')).toBe(1)
  })
})

describe('normalizeMetricValue', () => {
  it('converts a prefixed value to its base unit', () => {
    expect(normalizeMetricValue(2, 'MB')).toBe(2e6)
    expect(normalizeMetricValue(1500, 'ms')).toBe(1500)
  })
})

describe('baseUnit', () => {
  it('drops the prefix the value was scaled by', () => {
    expect(baseUnit('MB')).toBe('B')
    expect(baseUnit('k')).toBe('')
    expect(baseUnit('%')).toBe('%')
    expect(baseUnit('ms')).toBe('ms')
    expect(baseUnit(null)).toBe('')
  })
})

describe('isSingleCharSIPrefix', () => {
  it('recognises a unit that is nothing but a magnitude', () => {
    expect(isSingleCharSIPrefix('k')).toBe(true)
    expect(isSingleCharSIPrefix('B')).toBe(false)
    expect(isSingleCharSIPrefix('kB')).toBe(false)
  })
})

describe('splitMagnitude', () => {
  it('splits the value from its prefix, so a caller can join it to a symbol', () => {
    expect(splitMagnitude(60_400_000)).toEqual({ num: '60.4', prefix: 'M' })
    expect(splitMagnitude(0)).toEqual({ num: '0', prefix: '' })
  })

  it('shows more decimals the smaller the value', () => {
    expect(splitMagnitude(1.5).num).toBe('1.50')
    expect(splitMagnitude(15).num).toBe('15.0')
    expect(splitMagnitude(150).num).toBe('150')
  })
})

describe('fmtValueWithUnit', () => {
  it('folds the prefix onto the symbol, so the label reads as one unit', () => {
    expect(fmtValueWithUnit(60_400_000, 'B/s')).toBe('60.4 MB/s')
  })

  it('keeps a percentage next to its number', () => {
    expect(fmtValueWithUnit(42, '%')).toBe('42.0%')
  })

  it('renders a time unit whole, without an SI prefix', () => {
    expect(fmtValueWithUnit(933, 'ms')).toBe('933 ms')
  })

  it('reports a bare magnitude where there is no unit', () => {
    expect(fmtValueWithUnit(1500, '')).toBe('1.5k')
  })
})
