/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { type ComputedRef, computed, ref, watchEffect } from 'vue'

import { columnId } from '@/monitoring/shared/tableState/schema'

import { iconListWidth } from './iconList'

export const MODE_COLUMN_ID = 'modes'

export const MODE_ICONS_PER_ROW = 3

const CELL_PADDING = 16

export const EMPTY_MODE_COLUMN_WIDTH = 40
export const FILLED_MODE_COLUMN_WIDTH = iconListWidth(MODE_ICONS_PER_ROW) + CELL_PADDING

interface RowWithModes {
  modes?: readonly unknown[] | null | undefined
}

export function useModeColumnWidth(rows: () => readonly RowWithModes[]): ComputedRef<number> {
  const carriesModes = ref(false)

  watchEffect(() => {
    if (rows().some((row) => (row.modes?.length ?? 0) > 0)) {
      carriesModes.value = true
    }
  })

  return computed(() => (carriesModes.value ? FILLED_MODE_COLUMN_WIDTH : EMPTY_MODE_COLUMN_WIDTH))
}

export function sizeModeColumn<T>(columns: ColumnDef<T>[], width: number): ColumnDef<T>[] {
  return columns.map((column) =>
    columnId(column) === MODE_COLUMN_ID ? { ...column, minSize: width, maxSize: width } : column
  )
}
