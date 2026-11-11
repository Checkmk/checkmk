/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { type ComputedRef, type Ref, computed } from 'vue'

import { columnId } from '@/monitoring/shared/tableState/schema'

import { CELL_PADDING, SUBPIXEL_SLACK } from './MonitoringTableContext'
import type { TextWidth } from './timestampColumns'

/**
 * The width the site column needs for the longest of the site ids it can show. Null while text
 * can't be measured.
 */
export function useSiteColumnWidth(
  siteIds: readonly string[],
  textWidth: Readonly<Ref<TextWidth | null>>
): ComputedRef<number | null> {
  return computed(() => {
    const measure = textWidth.value
    if (!measure) {
      return null
    }
    const widest = siteIds.reduce((max, siteId) => Math.max(max, measure(siteId)), 0)
    return Math.ceil(widest) + SUBPIXEL_SLACK + CELL_PADDING
  })
}

/**
 * Fits each column in `widths` to the width of its content, but no wider than its own maximum,
 * and never narrower than its header needs. Until its content fits, it takes its share of the spare
 * width by its own `meta.grow`. Where the table is short of width, the column can still shrink to
 * its own minimum. A column without a width keeps its own sizes.
 *
 * `widths` is keyed by column id, which is the row field for a column defined by `accessorKey`
 * alone: a column with an `id` of its own can't be fitted this way.
 *
 * Not for a column with `meta.maxGrowth`, which takes precedence over the maximum the fit sets, nor
 * for one with `meta.headerHelp`, as the fit sets `meta.fitHeader`.
 */
export function fitColumnsToContent<T>(
  columns: ColumnDef<T>[],
  widths: Readonly<Partial<Record<keyof T & string, number | null>>>
): ColumnDef<T>[] {
  const widthOf: Readonly<Record<string, number | null | undefined>> = widths
  return columns.map((column) => {
    const width = widthOf[columnId(column) ?? '']
    if (width === undefined || width === null) {
      return column
    }
    const fit = Math.min(width, column.maxSize ?? Number.POSITIVE_INFINITY)
    return {
      ...column,
      minSize: Math.min(column.minSize ?? fit, fit),
      maxSize: fit,
      meta: { ...column.meta, fitHeader: true }
    }
  })
}
