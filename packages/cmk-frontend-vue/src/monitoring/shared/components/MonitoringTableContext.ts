/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { RowData, Updater } from '@tanstack/vue-table'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import type { ComputedRef, InjectionKey } from 'vue'

import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

import type { ColumnFilterDefinition } from './filter/types'

export type ColumnJustify = 'left' | 'center' | 'right'

declare module '@tanstack/vue-table' {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    headerTitle?: TranslatedString
    /** Markup-capable help shown via CmkHelpText next to the header label. */
    headerHelp?: TranslatedString
    pickerLabel?: TranslatedString
    justify?: ColumnJustify
    filter?: ColumnFilterDefinition
    selectColumn?: boolean
    hidden?: boolean
    /**
     * The column is never narrower than its header needs to show its label in full. Only for
     * columns that can't be sorted and have no `headerHelp`, since only there the label fills its
     * cell, and only in tables with column pinning.
     */
    fitHeader?: boolean
    /** The stretch column absorbs all remaining width. Ignored by MonitoringTable. */
    stretch?: boolean
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

export function resolveUpdater<S>(updater: Updater<S>, current: S): S {
  return typeof updater === 'function' ? (updater as (old: S) => S)(current) : updater
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

/** The width, per column id, that each `fitHeader` column needs to show its label in full. */
export type HeaderFitWidths = Record<string, number>

export const TABLE_BORDER_SPACING = 1
export const TABLE_BORDER_SPACING_PX = `${TABLE_BORDER_SPACING}px`

export interface ColumnLayoutInfo {
  width: number | null
  pinnedLeft: number | null
  pinnedRight: number | null
  isLastPinned: boolean
  isFirstPinnedRight: boolean
  justify: ColumnJustify
}

export const COLUMN_LAYOUT_KEY: InjectionKey<ComputedRef<Map<string, ColumnLayoutInfo>>> = Symbol(
  'monitoringTableColumnLayout'
)

/** Drag handlers provided by EditableTable for row reordering, consumed by DragHandleCell. */
export interface RowDragHandlers {
  dragStart: (event: DragEvent) => void
  drag: (event: DragEvent) => void
  dragEnd: (event: DragEvent) => void
}

export const ROW_DRAG_KEY: InjectionKey<RowDragHandlers> = Symbol('editableTableRowDrag')
