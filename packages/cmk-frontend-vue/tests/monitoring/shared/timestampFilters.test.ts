/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'

import type { ColumnFilterDefinition } from '@/monitoring/shared/components/filter/types'
import { filterTimestampsAsShown } from '@/monitoring/shared/timestampFilters'
import type { TimestampFormatId } from '@/monitoring/shared/types'

interface Row {
  name: string
  last_check: number
}

const columns: ColumnDef<Row>[] = [
  {
    accessorKey: 'name',
    header: 'Host',
    meta: { filter: { type: 'string-input', field: 'name' } }
  },
  {
    accessorKey: 'last_check',
    header: 'Check age',
    meta: { filter: { type: 'date-time-range', field: 'last_check' } }
  }
]

function filterOf(format: TimestampFormatId, id: string): ColumnFilterDefinition | undefined {
  return filterTimestampsAsShown(columns, format).find(
    (column) => 'accessorKey' in column && column.accessorKey === id
  )?.meta?.filter
}

test.each<TimestampFormatId>(['rel', 'mixed', 'both'])(
  'a timestamp shown as an age (%s) is filtered by duration',
  (format) => {
    expect(filterOf(format, 'last_check')).toEqual({ type: 'duration', field: 'last_check' })
  }
)

test.each<TimestampFormatId>(['abs', 'epoch'])(
  'a timestamp shown as a point in time (%s) keeps the date-time range filter',
  (format) => {
    expect(filterOf(format, 'last_check')).toEqual({
      type: 'date-time-range',
      field: 'last_check'
    })
  }
)

test('a column that is no timestamp keeps its filter', () => {
  expect(filterOf('rel', 'name')).toEqual({ type: 'string-input', field: 'name' })
})
