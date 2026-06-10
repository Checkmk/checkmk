/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { RowData } from '@tanstack/vue-table'
import type { ComputedRef, InjectionKey } from 'vue'

import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

import type { ColumnFilterDefinition } from './filter/types'

export type ColumnJustify = 'left' | 'center' | 'right'

declare module '@tanstack/vue-table' {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    justify?: ColumnJustify
    filter?: ColumnFilterDefinition
  }
}

const JUSTIFY_TO_FLEX: Readonly<Record<ColumnJustify, 'flex-start' | 'center' | 'flex-end'>> = {
  left: 'flex-start',
  center: 'center',
  right: 'flex-end'
}

export function justifyToFlex(justify: ColumnJustify): 'flex-start' | 'center' | 'flex-end' {
  return JUSTIFY_TO_FLEX[justify]
}

export type BreakpointToken = 's' | 'm' | 'l' | 'xl'

const BREAKPOINT_TOKEN_PX: Readonly<Record<BreakpointToken, number>> = {
  s: 320,
  m: 560,
  l: 800,
  xl: 1100
}

export type BreakpointValue = BreakpointToken | number

export function resolveBreakpoint(value: BreakpointValue): number {
  return typeof value === 'number' ? value : BREAKPOINT_TOKEN_PX[value]
}
export type CellBreakpoints = Readonly<Record<string, BreakpointValue>>

export const MONITORING_SERVICE: InjectionKey<MonitoringService<unknown>> =
  Symbol('MonitoringService')

export interface ColumnLayoutInfo {
  width: number | null
  pinnedLeft: number | null
  isLastPinned: boolean
  justify: ColumnJustify
}

export const COLUMN_LAYOUT_KEY: InjectionKey<ComputedRef<Map<string, ColumnLayoutInfo>>> = Symbol(
  'monitoringTableColumnLayout'
)
