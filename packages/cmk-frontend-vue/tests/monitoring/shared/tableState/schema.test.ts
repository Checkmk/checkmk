/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { describe, expect, it } from 'vitest'

import { buildOfferedLimits, buildTableStateSchema } from '@/monitoring/shared/tableState/schema'

interface Row {
  name: string
  alias: string
  site_id: string
}

const columns: ColumnDef<Row>[] = [
  {
    id: 'select',
    header: '',
    enableSorting: false,
    enableHiding: false,
    meta: { selectColumn: true }
  },
  { accessorKey: 'name', header: 'Host', enableHiding: false },
  { accessorKey: 'alias', header: 'Alias', meta: { hidden: true } },
  { accessorKey: 'site_id', header: 'Site', enableSorting: false }
]

describe('buildTableStateSchema', () => {
  it('collects hideable ids in table order, excluding non-hideable columns', () => {
    const schema = buildTableStateSchema({ columns, limitTiers: [1000], mayRemoveLimit: false })
    expect(schema.hideable).toEqual(['alias', 'site_id'])
  })

  it('marks a column sortable unless enableSorting is explicitly false', () => {
    const schema = buildTableStateSchema({ columns, limitTiers: [1000], mayRemoveLimit: false })
    expect(schema.sortable).toEqual(new Set(['name', 'alias']))
  })

  it('hides only the columns meta.hidden marks', () => {
    const schema = buildTableStateSchema({ columns, limitTiers: [1000], mayRemoveLimit: false })
    expect(schema.defaultVisibility).toEqual({ alias: false })
  })

  it('offers the given tiers, defaulting to DEFAULT_BATCH_SIZE when none are given', () => {
    expect(
      buildTableStateSchema({ columns, limitTiers: [], mayRemoveLimit: false }).offeredLimits
    ).toEqual([1000])
    expect(
      buildTableStateSchema({ columns, limitTiers: [1000, 5000], mayRemoveLimit: false })
        .offeredLimits
    ).toEqual([1000, 5000])
  })

  it('appends null when the user may remove the limit', () => {
    const schema = buildTableStateSchema({ columns, limitTiers: [1000], mayRemoveLimit: true })
    expect(schema.offeredLimits).toEqual([1000, null])
  })
})

describe('buildOfferedLimits', () => {
  it('falls back to DEFAULT_BATCH_SIZE when no tiers are given', () => {
    expect(buildOfferedLimits([], false)).toEqual([1000])
  })

  it('passes explicit tiers through unchanged', () => {
    expect(buildOfferedLimits([1000, 5000], false)).toEqual([1000, 5000])
  })

  it('appends null when the user may remove the limit', () => {
    expect(buildOfferedLimits([1000], true)).toEqual([1000, null])
  })
})
