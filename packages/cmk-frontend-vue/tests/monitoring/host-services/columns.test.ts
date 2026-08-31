/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { buildHostColumns } from '@/monitoring/all-hosts/columns'
import {
  buildHostServicesColumnPinning,
  useHostServicesColumns,
  visibleServiceFields
} from '@/monitoring/host-services/columns'
import type { HostServiceEntry } from '@/monitoring/shared/api/types'
import {
  MonitoringService,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'
import { columnId } from '@/monitoring/shared/tableState/schema'

import { makeKeyShortcutService, makeResponse } from '../shared/services/testHelpers'

class ServiceColumnService extends MonitoringService<HostServiceEntry> {
  constructor(columns: ColumnDef<HostServiceEntry>[], shortCuts: KeyShortcutService) {
    super('host-services-columns', shortCuts, { columns })
  }

  protected fetchBatch(): Promise<PagedResponse<HostServiceEntry>> {
    return Promise.resolve(makeResponse([], 0, 0))
  }
}

function serviceColumns(includeSelect = true): ColumnDef<HostServiceEntry>[] {
  return useHostServicesColumns({ includeSelect })
}

function makeService() {
  const service = new ServiceColumnService(serviceColumns(), makeKeyShortcutService())
  service.stopPolling()
  return service
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

test('the labels, tags and contact columns start hidden', () => {
  const service = makeService()

  expect(service.defaultColumnVisibility).toEqual({
    labels: false,
    tags: false,
    contacts: false,
    contact_groups: false
  })
  expect(service.columnVisibility.value).toEqual(service.defaultColumnVisibility)
})

test('a table on its defaults asks for none of their fields', () => {
  expect(visibleServiceFields(makeService().columnVisibility.value)).toEqual([])
})

test('a column the user shows asks for its field again', () => {
  expect(visibleServiceFields({ labels: false, tags: false, contacts: false })).toEqual([
    'contact_groups'
  ])
})

test('the state column reads as the one in the hosts listing', () => {
  const stateOf = (columns: ColumnDef<never>[]) => {
    const column = columns.find((candidate) => columnId(candidate) === 'state')!
    return {
      sortDescFirst: column.sortDescFirst,
      minSize: column.minSize,
      maxSize: column.maxSize,
      justify: column.meta?.justify
    }
  }

  expect(stateOf(serviceColumns() as ColumnDef<never>[])).toEqual(
    stateOf(
      buildHostColumns({
        includeSelect: true,
        includeActions: true,
        showCustomer: false,
        sites: []
      }) as ColumnDef<never>[]
    )
  )
})

test('the state column filter offers the state checkboxes plus flapping/stale flags', () => {
  const stateColumn = serviceColumns().find(
    (column) => columnId(column as ColumnDef<never>) === 'state'
  )

  expect(stateColumn?.meta?.filter).toEqual({
    type: 'checkbox-list-with-flags',
    field: 'state',
    options: [
      { value: 'OK', title: 'OK' },
      { value: 'WARN', title: 'WARN' },
      { value: 'CRIT', title: 'CRIT' },
      { value: 'UNKNOWN', title: 'UNKNOWN' }
    ],
    flags: [
      { field: 'is_flapping', title: 'Flapping' },
      { field: 'stale', title: 'Stale' }
    ]
  })
})

test('the mode column filter no longer offers flapping, which moved to the state column', () => {
  const modesColumn = serviceColumns().find(
    (column) => columnId(column as ColumnDef<never>) === 'modes'
  )

  expect(modesColumn?.meta?.filter).toEqual({
    type: 'boolean-group',
    groups: [
      { field: 'in_downtime', title: 'In downtime' },
      { field: 'acknowledged', title: 'Acknowledged' },
      { field: 'notifications_enabled', title: 'Notifications enabled' }
    ]
  })
})

test('the select column is neither rendered nor pinned when no action is permitted', () => {
  expect(serviceColumns(false).map(columnId)).not.toContain('select')
  expect(buildHostServicesColumnPinning({ includeSelect: false }).left).toEqual([
    'state',
    'modes',
    'name'
  ])
})

test('the hidden columns stay on offer in the picker', () => {
  expect(makeService().toggleableColumns.map((column) => column.id)).toEqual(
    expect.arrayContaining(['labels', 'tags', 'contacts', 'contact_groups'])
  )
})
