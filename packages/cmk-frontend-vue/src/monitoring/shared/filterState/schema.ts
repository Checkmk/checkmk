/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'

import type { FilterField } from '@/monitoring/shared/api/types'
import { filterFields } from '@/monitoring/shared/components/filter/types'

import type { FilterUrlSchema } from './types'

/**
 * The fields a table's filter vocabulary accepts, derived from the same
 * `ColumnDef[]` the table renders from - so a field a decoded URL names can
 * never drift out of sync with what the column filters actually offer.
 */
export function buildFilterUrlSchema<T>(columns: ColumnDef<T>[]): FilterUrlSchema {
  const filterableFields = new Set<FilterField>()
  for (const column of columns) {
    const filter = column.meta?.filter
    if (filter === undefined) {
      continue
    }
    for (const field of filterFields(filter)) {
      filterableFields.add(field)
    }
  }
  return { filterableFields }
}
