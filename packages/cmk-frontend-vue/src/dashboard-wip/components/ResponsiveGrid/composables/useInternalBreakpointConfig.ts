/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed } from 'vue'

import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { ResponsiveGridBreakpoint } from '@/dashboard-wip/types/dashboard'

import type { ResponsiveGridInternalBreakpoint } from '../types'
import { breakpointToInternal } from './utils'

type ConfiguredBreakpoints = DashboardConstants['responsive_grid_breakpoints']
type BreakpointToValue = Readonly<Record<ResponsiveGridInternalBreakpoint, number>>

export function useInternalBreakpointConfig(configuredBreakpoints: ConfiguredBreakpoints) {
  return computed(() => {
    const columns = Object.fromEntries(
      Object.entries(configuredBreakpoints).map(([key, value]) => [
        breakpointToInternal[key as ResponsiveGridBreakpoint],
        value.columns
      ])
    ) as BreakpointToValue

    const widths = Object.fromEntries(
      Object.entries(configuredBreakpoints).map(([key, value]) => [
        breakpointToInternal[key as ResponsiveGridBreakpoint],
        value.min_width
      ])
    ) as BreakpointToValue

    return {
      columns,
      widths
    }
  })
}
