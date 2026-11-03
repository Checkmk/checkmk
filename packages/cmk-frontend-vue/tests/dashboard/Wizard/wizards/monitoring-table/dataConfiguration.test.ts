/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  rowLimitChoice,
  rowLimitOf,
  showsTimestamps,
  withColumns
} from '@/dashboard/components/Wizard/wizards/monitoring-table/dataConfiguration'
import type { MonitoringTableContent } from '@/dashboard/types/widget'

const CONTENT: MonitoringTableContent = {
  type: 'monitoring_table',
  table: 'hosts',
  columns: ['state', 'address'],
  sort: ['address:desc', 'state:asc'],
  limit: 1000,
  date_format: '%Y-%m-%d',
  timestamp_format: 'mixed'
}

describe('row limit', () => {
  it.each([
    ['default', 1000],
    ['max', 5000]
  ] as const)('maps %s to %i rows', (choice, limit) => {
    expect(rowLimitOf(choice, Number.NaN)).toBe(limit)
  })

  it('takes a custom limit as it is', () => {
    expect(rowLimitOf('custom', 250)).toBe(250)
  })

  it.each([0, 42.4, 5001, Number.NaN, undefined])('rejects a custom limit of %s', (custom) => {
    expect(rowLimitOf('custom', custom)).toBeNull()
  })

  it('reopens a stored limit as a custom one unless it is a preset', () => {
    expect([1000, 5000, 250].map(rowLimitChoice)).toEqual(['default', 'max', 'custom'])
  })
})

describe('columns', () => {
  it('drops the sorter of a column no longer shown', () => {
    expect(withColumns(CONTENT, ['state'])).toEqual({
      ...CONTENT,
      columns: ['state'],
      sort: ['state:asc']
    })
  })

  it.each([
    [['state', 'last_check'], true],
    [['state', 'last_state_change'], true],
    [['state', 'address'], false]
  ])('offers the timestamp formats for the columns %j: %s', (columns, offered) => {
    expect(showsTimestamps({ ...CONTENT, columns })).toBe(offered)
  })
})
