/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import {
  type HostColumnOptions,
  buildHostColumnPinning,
  buildHostColumns,
  visibleHostFields
} from '@/monitoring/all-hosts/columns'
import type { HostEntry } from '@/monitoring/shared/api/types'
import {
  MonitoringService,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'
import { columnId } from '@/monitoring/shared/tableState/schema'

import { makeKeyShortcutService, makeResponse } from '../shared/services/testHelpers'

class HostColumnService extends MonitoringService<HostEntry> {
  constructor(columns: ColumnDef<HostEntry>[], shortCuts: KeyShortcutService) {
    super('all-hosts-columns', shortCuts, { columns })
  }

  protected fetchBatch(): Promise<PagedResponse<HostEntry>> {
    return Promise.resolve(makeResponse([], 0, 0))
  }
}

/** The columns of a table without multi-tenancy, unless a test asks for something else. */
function hostColumns(options: Partial<HostColumnOptions> = {}): ColumnDef<HostEntry>[] {
  return buildHostColumns({ includeActions: true, showCustomer: false, sites: [], ...options })
}

function makeService(options: Partial<HostColumnOptions> = {}) {
  const service = new HostColumnService(hostColumns(options), makeKeyShortcutService())
  service.stopPolling()
  return service
}

function columnIds(options: Partial<HostColumnOptions> = {}): (string | undefined)[] {
  return hostColumns(options).map(columnId)
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

test('no pinned column is offered in the picker', () => {
  const pinning = buildHostColumnPinning({ includeActions: true })
  const offered = makeService().toggleableColumns.map((column) => column.id)

  const pinned = [...(pinning.left ?? []), ...(pinning.right ?? [])]
  expect(pinned).not.toHaveLength(0)
  for (const id of pinned) {
    expect(offered).not.toContain(id)
  }
})

test('the optional columns are offered in the picker, labelled by their header', () => {
  const offered = makeService().toggleableColumns

  expect(offered).toEqual([
    { id: 'alias', label: 'Host alias' },
    { id: 'address', label: 'IP address' },
    { id: 'folder', label: 'Folder' },
    { id: 'site_id', label: 'Site' },
    { id: 'num_services', label: 'All services' },
    { id: 'num_services_ok', label: 'OK' },
    { id: 'num_services_warn', label: 'Wa' },
    { id: 'num_services_crit', label: 'Cr' },
    { id: 'num_services_unknown', label: 'Un' },
    { id: 'num_services_pending', label: 'Pd' },
    { id: 'last_check', label: 'Last check' },
    { id: 'last_state_change', label: 'Last state change' },
    { id: 'labels', label: 'Labels' },
    { id: 'tags', label: 'Tags' },
    { id: 'contacts', label: 'Contacts' },
    { id: 'contact_groups', label: 'Contact groups' }
  ])
})

test('most offered columns are shown on first use, but alias, folder, the timestamps and labels start hidden', () => {
  const service = makeService()

  expect(service.defaultColumnVisibility).toEqual({
    alias: false,
    folder: false,
    site_id: false,
    last_check: false,
    last_state_change: false,
    labels: false,
    tags: false,
    contacts: false,
    contact_groups: false
  })
  expect(service.columnVisibility.value).toEqual(service.defaultColumnVisibility)
})

test('the fixed columns keep their position around the optional ones', () => {
  expect(columnIds()).toEqual([
    'select',
    'state',
    'modes',
    'name',
    'alias',
    'address',
    'folder',
    'site_id',
    'num_services',
    'num_services_ok',
    'num_services_warn',
    'num_services_crit',
    'num_services_unknown',
    'num_services_pending',
    'last_check',
    'last_state_change',
    'labels',
    'tags',
    'contacts',
    'contact_groups',
    'actions'
  ])
})

test('every hideable column asks for its field while nothing is hidden', () => {
  // site_id is always present in every API response, so it is not an optional
  // field and does not appear in visibleHostFields.
  const optionalFieldColumns = makeService()
    .toggleableColumns.map((column) => column.id)
    .filter((id) => id !== 'site_id')
  expect(visibleHostFields({})).toEqual(optionalFieldColumns)
})

test('a hidden column stops asking for its field', () => {
  const fields = visibleHostFields({ address: false, num_services_pending: false })

  expect(fields).not.toContain('address')
  expect(fields).not.toContain('num_services_pending')
  expect(fields).toContain('num_services')
})

test('the fields of the fixed columns are never asked for, the API always sending them', () => {
  // Only what the API treats as optional can be requested; 'state', 'name',
  // 'site_id' and the modes come with every host either way.
  expect(visibleHostFields({})).not.toContain('state')
  expect(visibleHostFields({})).not.toContain('name')
  expect(visibleHostFields({})).not.toContain('modes')
  expect(visibleHostFields({})).not.toContain('site_id')
})

test('the actions column is neither rendered nor pinned when no row action is permitted', () => {
  expect(columnIds({ includeActions: false })).not.toContain('actions')
  expect(buildHostColumnPinning({ includeActions: false }).right).toBeUndefined()
})

test('the site column filter offers the configured sites as options', () => {
  const columns = hostColumns({
    sites: [
      { id: 'local', alias: 'Local site' },
      { id: 'remote', alias: 'Remote site' }
    ]
  })
  const siteColumn = columns.find((column) => columnId(column) === 'site_id')

  expect(siteColumn?.meta?.filter).toEqual({
    type: 'checkbox-list',
    field: 'site_id',
    options: [
      { value: 'local', title: 'Local site' },
      { value: 'remote', title: 'Remote site' }
    ]
  })
})

test('the state column filter offers the state checkboxes plus flapping/stale flags', () => {
  const columns = hostColumns({ includeActions: true })
  const stateColumn = columns.find((column) => columnId(column) === 'state')

  expect(stateColumn?.meta?.filter).toEqual({
    type: 'checkbox-list-with-flags',
    field: 'state',
    options: [
      { value: 'UP', title: 'UP' },
      { value: 'DOWN', title: 'DOWN' },
      { value: 'UNREACHABLE', title: 'UNREACH' }
    ],
    flags: [
      { field: 'is_flapping', title: 'Flapping' },
      { field: 'stale', title: 'Stale' }
    ]
  })
})

test('the mode column filter no longer offers flapping, which moved to the state column', () => {
  const columns = hostColumns({ includeActions: true })
  const modesColumn = columns.find((column) => columnId(column) === 'modes')

  expect(modesColumn?.meta?.filter).toEqual({
    type: 'boolean-group',
    groups: [
      { field: 'in_downtime', title: 'In downtime' },
      { field: 'acknowledged', title: 'Acknowledged' }
    ]
  })
})

test('the folder column offers a text filter', () => {
  const columns = hostColumns()
  const folderColumn = columns.find((column) => columnId(column) === 'folder')

  expect(folderColumn?.meta?.filter).toEqual({ type: 'string-input', field: 'folder' })
})

test.each(['last_check', 'last_state_change'])(
  'the %s column offers a from/to filter on the instant',
  (field) => {
    const columns = hostColumns()
    const column = columns.find((candidate) => columnId(candidate) === field)

    expect(column?.meta?.filter).toEqual({ type: 'date-time-range', field })
  }
)

test('a timestamp column stays hidden until the user shows it', () => {
  const columns = hostColumns()
  const column = columns.find((candidate) => columnId(candidate) === 'last_check')

  expect(column?.meta?.hidden).toBe(true)
})

test('the customer column is absent from a table without multi-tenancy', () => {
  expect(columnIds()).not.toContain('customer')
  expect(makeService().toggleableColumns.map((column) => column.id)).not.toContain('customer')
})

test('the customer column is offered last, before the actions, under multi-tenancy', () => {
  const offered = makeService({ showCustomer: true }).toggleableColumns

  expect(offered.at(-1)).toEqual({ id: 'customer', label: 'Customer' })
  expect(columnIds({ showCustomer: true }).slice(-3)).toEqual([
    'contact_groups',
    'customer',
    'actions'
  ])
})

test('the customer column stays hidden until the user shows it', () => {
  const service = makeService({ showCustomer: true })

  expect(service.defaultColumnVisibility).toMatchObject({ customer: false })
})

test('the customer field is never asked for, the API deriving it from the site', () => {
  expect(visibleHostFields({})).not.toContain('customer')
  expect(visibleHostFields({ customer: true })).not.toContain('customer')
})
