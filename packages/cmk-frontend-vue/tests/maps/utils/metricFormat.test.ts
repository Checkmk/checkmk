/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { MetricUnitSpec } from '@/maps/types/api'
import { renderMetricValue } from '@/maps/utils/metricFormat'

function spec(partial: Partial<MetricUnitSpec>): MetricUnitSpec {
  return {
    notation: 'si',
    symbol: '',
    precision: { type: 'auto', digits: 2 },
    scale: 1,
    ...partial
  }
}

describe('renderMetricValue', () => {
  it('renders IEC like the Checkmk GUI (memory in GiB, not decimal GB)', () => {
    expect(renderMetricValue(8927830016, spec({ notation: 'iec', symbol: 'B' }), 'B')).toBe(
      '8.31 GiB'
    )
  })

  it('renders SI bandwidth with the registered symbol', () => {
    expect(renderMetricValue(1950, spec({ notation: 'si', symbol: 'bits/s' }), '')).toBe(
      '1.95 kbits/s'
    )
  })

  it('applies the translation scale before formatting (ms perfdata, s registry)', () => {
    expect(renderMetricValue(20, spec({ notation: 'time', symbol: 's', scale: 0.001 }), 'ms')).toBe(
      '20 ms'
    )
  })

  it('falls back to the SI heuristic without a registry entry', () => {
    expect(renderMetricValue(8927830016, null, 'B')).toBe('8.93 GB')
  })

  it('routes raw time units through the CMK TimeFormatter without a registry entry', () => {
    // Never "4.5 kms" — time scales by 60, not 1000.
    expect(renderMetricValue(4500, null, 'ms')).toBe('4.5 s')
    expect(renderMetricValue(0.4, undefined, 'ms')).toBe('0.4 ms')
    expect(renderMetricValue(0.02, undefined, 'ms')).toBe('20 \u03bcs')
    expect(renderMetricValue(137, null, 's')).toBe('2 min 17 s')
    expect(renderMetricValue(259200, null, 's')).toBe('3 d')
    expect(renderMetricValue(350, null, 'us')).toBe('0.35 ms')
    expect(renderMetricValue(12, null, 'ns')).toBe('0.01 \u03bcs')
  })
})
