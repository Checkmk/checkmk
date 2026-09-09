/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  DashboardResponsiveGridLayout,
  ResponsiveGridBreakpoint
} from '@/dashboard/types/dashboard'

import type { ResponsiveGridInternalBreakpoint } from '../types'

/**
 * The single responsive layout every dashboard the frontend creates declares. The server
 * validates a widget's layouts against exactly these breakpoints, so both must stay in sync.
 */
export function defaultResponsiveGridLayout(): DashboardResponsiveGridLayout {
  return {
    type: 'responsive_grid',
    layouts: {
      default: {
        title: 'Default layout',
        breakpoints: ['M', 'XL', 'L', 'S', 'XS']
      }
    }
  }
}

// helper to get entries with correctly typed keys
export function typedEntries<T extends object>(obj: T): [keyof T, Required<T>[keyof T]][] {
  return Object.entries(obj) as [keyof T, T[keyof T]][]
}

export const breakpointFromInternal: Record<
  ResponsiveGridInternalBreakpoint,
  ResponsiveGridBreakpoint
> = {
  xxs: 'XS',
  xs: 'S',
  sm: 'M',
  md: 'L',
  lg: 'XL'
}
export const breakpointToInternal: Record<
  ResponsiveGridBreakpoint,
  ResponsiveGridInternalBreakpoint
> = {
  XS: 'xxs',
  S: 'xs',
  M: 'sm',
  L: 'md',
  XL: 'lg'
}
