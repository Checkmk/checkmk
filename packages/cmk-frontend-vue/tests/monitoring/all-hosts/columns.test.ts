/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, VisibilityState } from '@tanstack/vue-table'
import type { AllHostsFilterCondition } from 'cmk-shared-typing/typescript/monitoring/page_filter_condition'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import {
  type HostColumnOptions,
  buildHostColumnPinning,
  buildHostColumns,
  visibleHostFields
} from '@/monitoring/all-hosts/columns'
import { HostExport } from '@/monitoring/all-hosts/export/hostExport'
import type { HostEntry, HostOptionalField } from '@/monitoring/shared/api/types'
import { RowExport } from '@/monitoring/shared/export/rowExport'
import {
  MonitoringService,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'
import { columnId } from '@/monitoring/shared/tableState/schema'

import { listShownConditions } from '../shared/components/filter/shownConditions'
import { makeKeyShortcutService, makeResponse } from '../shared/services/testHelpers'

/**
 * The conditions of the shared schema that the column filters of All hosts show, as
 * `field:op`. See `listShownConditions` for how it is kept in step.
 */
const ALL_HOSTS_FILTER_CONDITIONS = {
  'acknowledged:eq': true,
  'active_checks_disabled:eq': true,
  'address:contains': true,
  'address:matches': true,
  'address:one_of': true,
  'alias:contains': true,
  'alias:matches': true,
  'alias:one_of': true,
  'contact_groups:all_of': true,
  'contact_groups:one_of': true,
  'contacts:contains': true,
  'contacts:matches': true,
  'contacts:one_of': true,
  'folder:contains': true,
  'folder:matches': true,
  'folder:one_of': true,
  'groups:all_of': true,
  'groups:one_of': true,
  'has_comments:eq': true,
  'in_check_period:eq': true,
  'in_downtime:eq': true,
  'in_notification_period:eq': true,
  'in_service_period:eq': true,
  'is_flapping:eq': true,
  'labels:all_of': true,
  'labels:one_of': true,
  'last_check:gte': true,
  'last_check:lte': true,
  'last_state_change:gte': true,
  'last_state_change:lte': true,
  'name:contains': true,
  'name:matches': true,
  'name:one_of': true,
  'notifications_enabled:eq': true,
  'num_services:eq': true,
  'num_services:gt': true,
  'num_services:gte': true,
  'num_services:lt': true,
  'num_services:lte': true,
  'num_services_crit:eq': true,
  'num_services_crit:gt': true,
  'num_services_crit:gte': true,
  'num_services_crit:lt': true,
  'num_services_crit:lte': true,
  'num_services_ok:eq': true,
  'num_services_ok:gt': true,
  'num_services_ok:gte': true,
  'num_services_ok:lt': true,
  'num_services_ok:lte': true,
  'num_services_pending:eq': true,
  'num_services_pending:gt': true,
  'num_services_pending:gte': true,
  'num_services_pending:lt': true,
  'num_services_pending:lte': true,
  'num_services_unknown:eq': true,
  'num_services_unknown:gt': true,
  'num_services_unknown:gte': true,
  'num_services_unknown:lt': true,
  'num_services_unknown:lte': true,
  'num_services_warn:eq': true,
  'num_services_warn:gt': true,
  'num_services_warn:gte': true,
  'num_services_warn:lt': true,
  'num_services_warn:lte': true,
  'passive_checks_disabled:eq': true,
  'site_id:one_of': true,
  'stale:eq': true,
  'state:one_of': true,
  'tags:all_of': true,
  'tags:one_of': true
} satisfies Record<AllHostsFilterCondition, true>

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
  return buildHostColumns({
    includeSelect: true,
    showCustomer: false,
    sites: [],
    showRelations: false,
    ...options
  })
}

function makeService(options: Partial<HostColumnOptions> = {}) {
  const service = new HostColumnService(hostColumns(options), makeKeyShortcutService())
  service.stopPolling()
  return service
}

function columnIds(options: Partial<HostColumnOptions> = {}): (string | undefined)[] {
  return hostColumns(options).map(columnId)
}

function requestedFields(
  visibility: VisibilityState = {},
  options: Partial<HostColumnOptions> = {}
): HostOptionalField[] {
  const offered = makeService(options).toggleableColumns.map((column) => column.id)
  return visibleHostFields(visibility, offered)
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

test('no pinned column is offered in the picker', () => {
  const pinning = buildHostColumnPinning({ includeSelect: true })
  const offered = makeService().toggleableColumns.map((column) => column.id)

  const pinned = [...(pinning.left ?? []), ...(pinning.right ?? [])]
  expect(pinned).not.toHaveLength(0)
  for (const id of pinned) {
    expect(offered).not.toContain(id)
  }
})

test('the optional columns are offered in the picker, abbreviated headers spelled out', () => {
  const offered = makeService().toggleableColumns

  expect(offered).toEqual([
    { id: 'alias', label: 'Host alias' },
    { id: 'address', label: 'IP address' },
    { id: 'indicator', label: 'Indicator' },
    { id: 'folder', label: 'Folder' },
    { id: 'site_id', label: 'Site' },
    { id: 'last_check', label: 'Check age' },
    { id: 'last_state_change', label: 'State age' },
    { id: 'labels', label: 'Labels' },
    { id: 'tags', label: 'Tags' },
    { id: 'contacts', label: 'Contacts' },
    { id: 'contact_groups', label: 'Contact groups' },
    { id: 'groups', label: 'Host groups' },
    { id: 'num_services', label: 'All services' },
    { id: 'num_services_ok', label: 'OK' },
    { id: 'num_services_warn', label: 'Warning (Wa)' },
    { id: 'num_services_crit', label: 'Critical (Cr)' },
    { id: 'num_services_unknown', label: 'Unknown (Un)' },
    { id: 'num_services_pending', label: 'Pending (Pd)' }
  ])
})

test('most offered columns are shown on first use, but alias, folder, the timestamps and labels start hidden', () => {
  const service = makeService()

  expect(service.defaultColumnVisibility).toEqual({
    alias: false,
    indicator: false,
    folder: false,
    site_id: false,
    last_check: false,
    last_state_change: false,
    labels: false,
    tags: false,
    contacts: false,
    contact_groups: false,
    groups: false
  })
  expect(service.columnVisibility.value).toEqual(service.defaultColumnVisibility)
})

test('the fixed columns keep their position around the optional ones', () => {
  expect(columnIds()).toEqual([
    'select',
    'state',
    'name',
    'alias',
    'address',
    'indicator',
    'folder',
    'site_id',
    'last_check',
    'last_state_change',
    'labels',
    'tags',
    'contacts',
    'contact_groups',
    'groups',
    'num_services',
    'num_services_ok',
    'num_services_warn',
    'num_services_crit',
    'num_services_unknown',
    'num_services_pending',
    'actions'
  ])
})

test('every hideable column asks for its field while nothing is hidden', () => {
  // site_id and the modes are always present in every API response, so they are not optional
  // fields and do not appear in visibleHostFields.
  const optionalFieldColumns = makeService({ showRelations: true })
    .toggleableColumns.map((column) => column.id)
    .filter((id) => id !== 'site_id' && id !== 'indicator')

  expect(requestedFields({}, { showRelations: true })).toEqual(optionalFieldColumns)
})

test('a column the table does not offer at all asks for no field', () => {
  expect(requestedFields()).not.toContain('num_relations')
  expect(requestedFields({}, { showRelations: true })).toContain('num_relations')
})

test('a hidden column stops asking for its field', () => {
  const fields = requestedFields({ address: false, num_services_pending: false })

  expect(fields).not.toContain('address')
  expect(fields).not.toContain('num_services_pending')
  expect(fields).toContain('num_services')
})

test('the fields of the fixed columns are never asked for, the API always sending them', () => {
  // Only what the API treats as optional can be requested; 'state', 'name',
  // 'site_id' and the modes come with every host either way.
  expect(requestedFields()).not.toContain('state')
  expect(requestedFields()).not.toContain('name')
  expect(requestedFields()).not.toContain('modes')
  expect(requestedFields()).not.toContain('site_id')
})

test('the actions column is rendered and pinned for a user permitted no command', () => {
  // Its overflow menu lists the links every host offers, such as the parent/child topology.
  expect(columnIds({ includeSelect: false })).toContain('actions')
  expect(buildHostColumnPinning({ includeSelect: false }).right).toEqual(['actions'])
})

test('the select column is neither rendered nor pinned when no action is permitted', () => {
  expect(columnIds({ includeSelect: false })).not.toContain('select')
  expect(buildHostColumnPinning({ includeSelect: false }).left).toEqual(['state', 'name'])
})

test('the indicator column is shown on first use when any host has custom icons', () => {
  expect(makeService({ showIndicators: true }).defaultColumnVisibility).not.toHaveProperty(
    'indicator'
  )
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

test('the state column filter offers the state checkboxes plus the flags of its icons, in their order', () => {
  const columns = hostColumns()
  const stateColumn = columns.find((column) => columnId(column) === 'state')

  expect(stateColumn?.meta?.filter).toEqual({
    type: 'checkbox-list-with-flags',
    field: 'state',
    options: [
      { value: 'UP', title: 'UP' },
      { value: 'DOWN', title: 'DOWN' },
      { value: 'UNREACHABLE', title: 'UNREACH' },
      { value: 'PENDING', title: 'PENDING' }
    ],
    flags: [
      { field: 'stale', title: 'Stale' },
      { field: 'is_flapping', title: 'Flapping' },
      { field: 'acknowledged', title: 'Acknowledged' },
      { field: 'in_downtime', title: 'In downtime' },
      { field: 'has_comments', title: 'Has comments' }
    ]
  })
})

test('the Indicator column filter no longer offers what moved to the state column', () => {
  const columns = hostColumns()
  const indicator = columns.find((column) => columnId(column) === 'indicator')

  expect(indicator?.meta?.filter).toEqual({
    type: 'boolean-group',
    combineLabel: 'Combine selections with',
    groups: [
      { field: 'notifications_enabled', title: 'Notifications disabled', negated: true },
      { field: 'active_checks_disabled', title: 'Active checks disabled' },
      { field: 'passive_checks_disabled', title: 'Passive checks disabled' },
      { field: 'in_notification_period', title: 'Out of notification period', negated: true },
      { field: 'in_service_period', title: 'Out of service period', negated: true },
      { field: 'in_check_period', title: 'Out of check period', negated: true }
    ]
  })
})

test('the folder column offers a text filter', () => {
  const columns = hostColumns()
  const folderColumn = columns.find((column) => columnId(column) === 'folder')

  expect(folderColumn?.meta?.filter).toEqual({ type: 'string-input', field: 'folder' })
})

test('the contacts column keeps its substring search', () => {
  const columns = hostColumns()
  const contactsColumn = columns.find((column) => columnId(column) === 'contacts')

  expect(contactsColumn?.meta?.filter).toEqual({ type: 'string-input', field: 'contacts' })
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

test('the relations column is absent while no host carries a relation', () => {
  expect(columnIds()).not.toContain('num_relations')
})

test('the relations column follows the host name', () => {
  const ids = columnIds({ showRelations: true })

  expect(ids.indexOf('num_relations')).toBe(ids.indexOf('name') + 1)
})

test('the relations column can be sorted on', () => {
  const columns = hostColumns({ showRelations: true })
  const column = columns.find((candidate) => columnId(candidate) === 'num_relations')

  expect(column).toBeDefined()
  expect(column?.enableSorting).not.toBe(false)
})

test('the customer column is absent from a table without multi-tenancy', () => {
  expect(columnIds()).not.toContain('customer')
  expect(makeService().toggleableColumns.map((column) => column.id)).not.toContain('customer')
})

test('the customer column is offered last, before the actions, under multi-tenancy', () => {
  const offered = makeService({ showCustomer: true }).toggleableColumns

  expect(offered.at(-1)).toEqual({ id: 'customer', label: 'Customer' })
  expect(columnIds({ showCustomer: true }).slice(-3)).toEqual([
    'num_services_pending',
    'customer',
    'actions'
  ])
})

test('the customer column stays hidden until the user shows it', () => {
  const service = makeService({ showCustomer: true })

  expect(service.defaultColumnVisibility).toMatchObject({ customer: false })
})

test('the customer field is never asked for, the API deriving it from the site', () => {
  expect(requestedFields()).not.toContain('customer')
  expect(requestedFields({ customer: true }, { showCustomer: true })).not.toContain('customer')
})

test('the export carries every data column of the table in table order', () => {
  const options = { showCustomer: true, showRelations: true }
  const dataColumns = columnIds(options).filter((id) => id !== 'select' && id !== 'actions')

  expect(RowExport.shownColumns(hostColumns(options), {}, HostExport.isColumn)).toEqual(dataColumns)
})

test('shows in its column filters the conditions the shared schema names', () => {
  const shown = hostColumns({ showCustomer: true, showRelations: true }).flatMap((column) =>
    column.meta?.filter ? listShownConditions(column.meta.filter) : []
  )

  expect([...new Set(shown)].sort()).toEqual(Object.keys(ALL_HOSTS_FILTER_CONDITIONS).sort())
})
