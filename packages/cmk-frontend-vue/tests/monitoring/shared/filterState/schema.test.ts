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
  { accessorKey: 'address', header: 'IP address' }
]

describe('buildFilterUrlSchema', () => {
  it('collects every field a column filter targets, including a multi-field group', () => {
    const schema = buildFilterUrlSchema(columns)
    expect(schema.filterableFields).toEqual(
      new Set(['name', 'state', 'in_downtime', 'acknowledged'])
    )
  })

  it('ignores columns without a filter', () => {
    const schema = buildFilterUrlSchema([{ accessorKey: 'address', header: 'IP address' }])
    expect(schema.filterableFields).toEqual(new Set())
  })
})
