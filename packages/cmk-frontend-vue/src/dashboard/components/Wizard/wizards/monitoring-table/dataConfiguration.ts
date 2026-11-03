/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MonitoringTableContent } from '@/dashboard/types/widget'
import type { MonitoringTableColumn } from '@/monitoring/table-widget/tableDescriptors'

import { DEFAULT_ROW_LIMIT } from './monitoringTables'

export const MAX_ROW_LIMIT = 5000

export type RowLimitChoice = 'default' | 'max' | 'custom'

export type SortDirection = 'asc' | 'desc'

export interface Sorter {
  column: string
  direction: SortDirection
}

export function rowLimitChoice(limit: number): RowLimitChoice {
  return limit === DEFAULT_ROW_LIMIT ? 'default' : limit === MAX_ROW_LIMIT ? 'max' : 'custom'
}

export function isValidRowLimit(limit: number | undefined): limit is number {
  return Number.isInteger(limit) && limit! >= 1 && limit! <= MAX_ROW_LIMIT
}

/** The limit the choice stands for, null for an invalid custom limit. */
export function rowLimitOf(choice: RowLimitChoice, customLimit: number | undefined): number | null {
  return {
    default: DEFAULT_ROW_LIMIT,
    max: MAX_ROW_LIMIT,
    custom: isValidRowLimit(customLimit) ? customLimit : null
  }[choice]
}

export function parseSorters(sort: readonly string[]): Sorter[] {
  return sort.map((token) => {
    const [column = '', direction] = token.split(':')
    return { column, direction: direction === 'desc' ? 'desc' : 'asc' }
  })
}

export function encodeSorters(sorters: readonly Sorter[]): string[] {
  return sorters.map(({ column, direction }) => `${column}:${direction}`)
}

/** A column that is no longer shown cannot sort the table either. */
export function withColumns(
  content: MonitoringTableContent,
  columns: readonly string[]
): MonitoringTableContent {
  return {
    ...content,
    columns: [...columns],
    sort: encodeSorters(parseSorters(content.sort).filter(({ column }) => columns.includes(column)))
  }
}

/** The columns the date and timestamp format apply to. */
const TIMESTAMP_COLUMNS: ReadonlySet<string> = new Set(['last_check', 'last_state_change'])

export function showsTimestamps(content: MonitoringTableContent): boolean {
  return content.columns.some((column) => TIMESTAMP_COLUMNS.has(column))
}

export function sortableColumns(
  content: MonitoringTableContent,
  catalog: readonly MonitoringTableColumn[]
): MonitoringTableColumn[] {
  return catalog.filter((column) => column.sortable && content.columns.includes(column.id))
}

export function withSorters(
  content: MonitoringTableContent,
  sorters: readonly Sorter[]
): MonitoringTableContent {
  return { ...content, sort: encodeSorters(sorters) }
}
