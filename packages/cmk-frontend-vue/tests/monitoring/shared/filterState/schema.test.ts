/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { describe, expect, it } from 'vitest'

import { buildFilterUrlSchema } from '@/monitoring/shared/filterState/schema'

interface Row {
  name: string
  state: string
  modes: unknown
  address: string
  last_state_change: number
  last_check: number
}

const columns: ColumnDef<Row>[] = [
  {
    accessorKey: 'name',
    header: 'Host',
    meta: { filter: { type: 'string-input', field: 'name' } }
  },
  {
    accessorKey: 'state',
    header: 'State',
    meta: { filter: { type: 'checkbox-list', field: 'state', options: [] } }
  },
  {
    accessorKey: 'modes',
    header: 'Mode',
    meta: {
      filter: {
        type: 'boolean-group',
        groups: [
          { field: 'in_downtime', title: 'In downtime' },
          { field: 'acknowledged', title: 'Acknowledged' }
        ]
      }
    }
  },
  { accessorKey: 'address', header: 'IP address' },
  {
    accessorKey: 'last_state_change',
    header: 'State age',
    meta: { filter: { type: 'duration', field: 'last_state_change' } }
  },
  {
    accessorKey: 'last_check',
    header: 'Last check',
    meta: { filter: { type: 'date-time-range', field: 'last_check' } }
  }
]

describe('buildFilterUrlSchema', () => {
  it('collects every field a column filter targets, including a multi-field group', () => {
    const schema = buildFilterUrlSchema(columns)
    expect(schema.filterableFields).toEqual(
      new Set(['name', 'state', 'in_downtime', 'acknowledged', 'last_state_change', 'last_check'])
    )
  })

  it('collects the timestamp fields, shown as a duration or a date range, as age fields', () => {
    const schema = buildFilterUrlSchema(columns)
    expect(schema.ageFields).toEqual(new Set(['last_state_change', 'last_check']))
  })

  it('ignores columns without a filter', () => {
    const schema = buildFilterUrlSchema([{ accessorKey: 'address', header: 'IP address' }])
    expect(schema.filterableFields).toEqual(new Set())
    expect(schema.ageFields).toEqual(new Set())
  })
})
