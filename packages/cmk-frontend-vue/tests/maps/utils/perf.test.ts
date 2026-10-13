/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { fmtSI, getMetric, parsePerfData, utilPercent } from '@/maps/utils/perf'

describe('parsePerfData', () => {
  it('returns empty array for empty string', () => {
    expect(parsePerfData('')).toEqual([])
  })

  it('parses a single metric', () => {
    const result = parsePerfData('rta=1.5ms;50;200;0;')
    expect(result).toHaveLength(1)
    expect(result[0]).toMatchObject({
      label: 'rta',
      value: 1.5,
      unit: 'ms',
      warn: 50,
      crit: 200
    })
  })

  it('parses a quoted label with spaces', () => {
    const result = parsePerfData("'load average'=0.5;1.5;2.0")
    expect(result[0]!.label).toBe('load average')
    expect(result[0]!.value).toBe(0.5)
  })

  it('parses multiple metrics', () => {
    const result = parsePerfData('load1=0.5;1;2 load5=0.3;1;2')
    expect(result).toHaveLength(2)
    expect(result[0]!.label).toBe('load1')
    expect(result[1]!.label).toBe('load5')
  })

  it('handles missing warn/crit as null', () => {
    const result = parsePerfData('mem=500MB')
    expect(result[0]!.warn).toBeNull()
    expect(result[0]!.crit).toBeNull()
  })

  it('parses percent unit', () => {
    const result = parsePerfData('usage=75%')
    expect(result[0]!.value).toBe(75)
    expect(result[0]!.unit).toBe('%')
  })
})

describe('getMetric', () => {
  it('returns null for empty array', () => {
    expect(getMetric([])).toBeNull()
  })

  it('returns first metric when no label given', () => {
    const metrics = parsePerfData('rta=1ms load=0.5')
    expect(getMetric(metrics)?.label).toBe('rta')
  })

  it('finds metric by label', () => {
    const metrics = parsePerfData('rta=1ms load=0.5')
    expect(getMetric(metrics, 'load')?.value).toBe(0.5)
  })

  it('returns first metric when label not found', () => {
    const metrics = parsePerfData('rta=1ms')
    expect(getMetric(metrics, 'nonexistent')?.label).toBe('rta')
  })
})

describe('utilPercent', () => {
  it('uses max when available', () => {
    const m = { label: 'x', value: 50, unit: '', warn: null, crit: null, min: 0, max: 100 }
    expect(utilPercent(m)).toBe(50)
  })

  it('uses crit when max is absent', () => {
    const m = { label: 'x', value: 150, unit: '', warn: null, crit: 200, min: null, max: null }
    expect(utilPercent(m)).toBe(75)
  })

  it('uses value directly for percent unit', () => {
    const m = {
      label: 'x',
      value: 80,
      unit: '%',
      warn: null,
      crit: null,
      min: null,
      max: null
    }
    expect(utilPercent(m)).toBe(80)
  })

  it('returns 0 when no reference point', () => {
    const m = {
      label: 'x',
      value: 50,
      unit: 'ms',
      warn: null,
      crit: null,
      min: null,
      max: null
    }
    expect(utilPercent(m)).toBe(0)
  })

  it('clamps to 100', () => {
    const m = {
      label: 'x',
      value: 200,
      unit: '%',
      warn: null,
      crit: null,
      min: null,
      max: null
    }
    expect(utilPercent(m)).toBe(100)
  })
})

describe('fmtSI', () => {
  it('keeps percent values plain', () => {
    expect(fmtSI(53.88, '%')).toBe('54%')
  })

  it('scales large values with SI prefixes', () => {
    expect(fmtSI(8927830016, 'B')).toBe('8.93 GB')
    expect(fmtSI(244340, '')).toBe('244k')
    expect(fmtSI(1500000, 'bit/s')).toBe('1.5 Mbit/s')
  })

  it('keeps small values unscaled', () => {
    expect(fmtSI(0.02, 'ms')).toBe('0.02 ms')
    expect(fmtSI(25, '')).toBe('25')
  })

  it('trims trailing zeros only after the decimal point', () => {
    expect(fmtSI(5, 'KB')).toBe('5 KB')
    expect(fmtSI(5.1, 'KB')).toBe('5.1 KB')
    // Integers ending in zero must keep their digits (regression: "250" → "25").
    expect(fmtSI(250e9, 'B')).toBe('250 GB')
    expect(fmtSI(100000, '')).toBe('100k')
  })

  it('does not stack SI prefixes onto already-prefixed units', () => {
    expect(fmtSI(2048, 'MB')).toBe('2048 MB')
    expect(fmtSI(1.5, 'GiB')).toBe('1.5 GiB')
  })
})
