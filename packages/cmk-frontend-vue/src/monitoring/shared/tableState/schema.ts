/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, VisibilityState } from '@tanstack/vue-table'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { DEFAULT_BATCH_SIZE } from '@/monitoring/shared/constants'
import type { RequestedLimit } from '@/monitoring/shared/types'

import type { TableStateSchema } from './types'

export interface ToggleableColumn {
  id: string
  label: TranslatedString
}

export function columnId<T>(column: ColumnDef<T>): string | undefined {
  if (column.id !== undefined) {
    return column.id
  }
  if ('accessorKey' in column && column.accessorKey !== undefined) {
    return String(column.accessorKey)
  }
  return undefined
}

function columnLabel<T>(column: ColumnDef<T>, id: string): string {
  if (typeof column.header === 'string' && column.header !== '') {
    return column.header
  }
  return column.meta?.headerTitle?.toString() ?? id
}

function isToggleable<T>(column: ColumnDef<T>): boolean {
  return !column.meta?.selectColumn && column.enableHiding !== false
}

export function buildToggleableColumns<T>(columns: ColumnDef<T>[]): ToggleableColumn[] {
  const result: ToggleableColumn[] = []
  for (const column of columns) {
    if (!isToggleable(column)) {
      continue
    }
    const id = columnId(column)
    if (id === undefined) {
      continue
    }
    result.push({ id, label: untranslated(columnLabel(column, id)) })
  }
  return result
}

export function computeDefaultVisibility<T>(columns: ColumnDef<T>[]): VisibilityState {
  const visibility: VisibilityState = {}
  for (const column of columns) {
    if (column.meta?.hidden) {
      const id = columnId(column)
      if (id !== undefined) {
        visibility[id] = false
      }
    }
  }
  return visibility
}

/**
 * The row-count tiers a table offers: the configured tiers (or the batch-size
 * default when none are configured), with "no limit" appended when the caller
 * may remove it.
 */
export function buildOfferedLimits(
  limitTiers: number[],
  mayRemoveLimit: boolean
): RequestedLimit[] {
  const numericTiers: RequestedLimit[] = limitTiers.length ? [...limitTiers] : [DEFAULT_BATCH_SIZE]
  return mayRemoveLimit ? [...numericTiers, null] : numericTiers
}

export interface BuildTableStateSchemaOptions<T> {
  columns: ColumnDef<T>[]
  limitTiers: number[]
  mayRemoveLimit: boolean
}

/**
 * The vocabulary a table offers for its non-filter display state: which
 * columns exist to hide, which can be sorted, and which row-count tiers are
 * on offer. Built from the same {@link ColumnDef} array the table itself
 * renders from, so a hideable or sortable column can never drift out of
 * sync with what the URL encoding accepts.
 */
export function buildTableStateSchema<T>({
  columns,
  limitTiers,
  mayRemoveLimit
}: BuildTableStateSchemaOptions<T>): TableStateSchema {
  const sortable = new Set<string>()
  for (const column of columns) {
    if (column.enableSorting === false) {
      continue
    }
    const id = columnId(column)
    if (id !== undefined) {
      sortable.add(id)
    }
  }

  return {
    hideable: buildToggleableColumns(columns).map(({ id }) => id),
    sortable,
    defaultVisibility: computeDefaultVisibility(columns),
    offeredLimits: buildOfferedLimits(limitTiers, mayRemoveLimit)
  }
}
