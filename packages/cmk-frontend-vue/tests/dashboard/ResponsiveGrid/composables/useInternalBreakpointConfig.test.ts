/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  computeColumnsPerBreakpoint,
  useInternalBreakpointConfig
} from '@/dashboard/components/ResponsiveGrid/composables/useInternalBreakpointConfig'
import type { DashboardConstants } from '@/dashboard/types/dashboard'

type ConfiguredBreakpoints = DashboardConstants['responsive_grid_breakpoints']

const sampleBreakpoints: ConfiguredBreakpoints = {
  XS: { columns: 4, min_width: 0 },
  S: { columns: 6, min_width: 480 },
  M: { columns: 8, min_width: 768 },
  L: { columns: 12, min_width: 1024 },
  XL: { columns: 16, min_width: 1440 }
}

describe('computeColumnsPerBreakpoint', () => {
  it('should map external breakpoints to internal breakpoints with column counts', () => {
    const result = computeColumnsPerBreakpoint(sampleBreakpoints)

    expect(result).toEqual({
      xxs: 4,
      xs: 6,
      sm: 8,
      md: 12,
      lg: 16
    })
  })

  it('should handle a subset of breakpoints', () => {
    const partial: ConfiguredBreakpoints = {
      L: { columns: 12, min_width: 1024 },
      XL: { columns: 16, min_width: 1440 }
    } as ConfiguredBreakpoints

    const result = computeColumnsPerBreakpoint(partial)

    expect(result).toEqual({
      md: 12,
      lg: 16
    })
  })
})

describe('useInternalBreakpointConfig', () => {
  it('should return a computed with columns and widths', () => {
    const config = useInternalBreakpointConfig(sampleBreakpoints)

    expect(config.value.columns).toEqual({
      xxs: 4,
      xs: 6,
      sm: 8,
      md: 12,
      lg: 16
    })

    expect(config.value.widths).toEqual({
      xxs: 0,
      xs: 480,
      sm: 768,
      md: 1024,
      lg: 1440
    })
  })
})
