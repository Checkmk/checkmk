/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { expect, test } from 'vitest'

import { withTimestampHeaders } from '@/monitoring/shared/timestampLabels'
import type { TimestampFormatId } from '@/monitoring/shared/types'

interface Row {
  name: string
  last_check: number
  last_state_change: number
}

const COLUMNS: ColumnDef<Row>[] = [
  { accessorKey: 'name', header: 'Name' },
  { accessorKey: 'last_check', header: 'Check age', meta: { headerTitle: 'Age of the check' } },
  { accessorKey: 'last_state_change', header: 'State age', meta: { justify: 'right' } }
] as ColumnDef<Row>[]

function headers(format: TimestampFormatId): [unknown, unknown][] {
  return withTimestampHeaders(COLUMNS, format).map((column) => [
    column.header?.toString(),
    column.meta?.headerTitle?.toString()
  ])
}

test('names relative timestamps as ages, with a hover text', () => {
  expect(headers('rel')).toEqual([
    ['Name', undefined],
    ['Check age', 'Age of the check'],
    ['State age', 'Age of the state']
  ])
})

test.each<TimestampFormatId>(['abs', 'mixed', 'both', 'epoch'])(
  'names %s timestamps by when they happened, without a hover text',
  (format) => {
    expect(headers(format)).toEqual([
      ['Name', undefined],
      ['Last check', undefined],
      ['Last state change', undefined]
    ])
  }
)

test('keeps the rest of the column meta', () => {
  const [, , lastStateChange] = withTimestampHeaders(COLUMNS, 'abs')

  expect(lastStateChange?.meta?.justify).toBe('right')
})
