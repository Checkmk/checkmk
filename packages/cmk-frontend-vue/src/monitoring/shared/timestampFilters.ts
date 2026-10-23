/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'

import type { TimestampFormatId } from '@/monitoring/shared/types'

const FORMATS_SHOWING_AGES: ReadonlySet<TimestampFormatId> = new Set(['rel', 'mixed', 'both'])

export function filterTimestampsAsShown<T>(
  columns: ColumnDef<T>[],
  timestampFormat: TimestampFormatId
): ColumnDef<T>[] {
  if (!FORMATS_SHOWING_AGES.has(timestampFormat)) {
    return columns
  }
  return columns.map((column) => {
    const filter = column.meta?.filter
    return filter?.type === 'date-time-range'
      ? { ...column, meta: { ...column.meta, filter: { type: 'duration', field: filter.field } } }
      : column
  })
}
