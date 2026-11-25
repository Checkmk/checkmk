/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { HostServicesFilterCondition } from 'cmk-shared-typing/typescript/monitoring/page_filter_condition'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { buildHostColumns } from '@/monitoring/all-hosts/columns'
import {
  buildHostServicesColumnPinning,
  requestedServiceFields,
  uncapNameWithoutSummary,
  useHostServicesColumns,
  visibleServiceFields
} from '@/monitoring/host-services/columns'
import { ServiceExport } from '@/monitoring/host-services/export/serviceExport'
import type { HostServiceEntry } from '@/monitoring/shared/api/types'
import { ACTIONS_HEADER_WIDTH } from '@/monitoring/shared/constants'
import { RowExport } from '@/monitoring/shared/export/rowExport'
import {
  MonitoringService,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'
import { buildTableStateSchema, columnId } from '@/monitoring/shared/tableState/schema'
import type { TableStateSchema } from '@/monitoring/shared/tableState/types'

import { listShownConditions } from '../shared/components/filter/shownConditions'
import { makeKeyShortcutService, makeResponse } from '../shared/services/testHelpers'

/**
 * The conditions of the shared schema that the column filters of Services of host show, as
 * `field:op`. See `listShownConditions` for how it is kept in step.
 */
const HOST_SERVICES_FILTER_CONDITIONS = {
  'acknowledged:eq': true,
  'active_checks_disabled:eq': true,
  'check_crashed:eq': true,
  'contact_groups:all_of': true,
  'contact_groups:one_of': true,
  'contacts:contains': true,
  'contacts:matches': true,
  'contacts:one_of': true,
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
  'passive_checks_disabled:eq': true,
  'stale:eq': true,
  'state:one_of': true,
  'summary:contains': true,
  'summary:matches': true,
  'summary:one_of': true,
  'tags:all_of': true,
  'tags:one_of': true
} satisfies Record<HostServicesFilterCondition, true>

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

/** The display vocabulary the picker and the URL codec read off the columns. */
function schemaOf(includeSelect: boolean): TableStateSchema {
  return buildTableStateSchema({
    columns: serviceColumns(includeSelect),
    limitTiers: [1000],
    mayRemoveLimit: false
  })
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

test('the indicator, labels, tags, contact and group columns start hidden', () => {
  const service = makeService()

  expect(service.defaultColumnVisibility).toEqual({
    indicator: false,
    labels: false,
    tags: false,
    contacts: false,
    contact_groups: false,
    groups: false
  })
  expect(service.columnVisibility.value).toEqual(service.defaultColumnVisibility)
})

test('a table on its defaults asks for none of their fields', () => {
  expect(visibleServiceFields(makeService().columnVisibility.value)).toEqual([])
})

test('a column the user shows asks for its field again', () => {
  expect(
    visibleServiceFields({ labels: false, tags: false, contacts: false, groups: false })
  ).toEqual(['contact_groups'])
})

test('every row asks for its graphs link and custom icons, whichever columns are shown', () => {
  expect(requestedServiceFields(makeService().columnVisibility.value)).toEqual([
    'graphs_link',
    'custom_icons'
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
        showCustomer: false,
        sites: [],
        showRelations: false
      }) as ColumnDef<never>[]
    )
  )
})

test('the state column filter offers the state checkboxes plus the flags of its icons, in their order', () => {
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
      { value: 'UNKNOWN', title: 'UNKNOWN' },
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
  const indicator = serviceColumns().find(
    (column) => columnId(column as ColumnDef<never>) === 'indicator'
  )

  expect(indicator?.meta?.filter).toEqual({
    type: 'boolean-group',
    combineLabel: 'Combine selections with',
    groups: [
      { field: 'notifications_enabled', title: 'Notifications disabled', negated: true },
      { field: 'active_checks_disabled', title: 'Active checks disabled' },
      { field: 'passive_checks_disabled', title: 'Passive checks disabled' },
      { field: 'in_notification_period', title: 'Out of notification period', negated: true },
      { field: 'in_service_period', title: 'Out of service period', negated: true },
      { field: 'in_check_period', title: 'Out of check period', negated: true },
      { field: 'check_crashed', title: 'Check crashed' }
    ]
  })
})

test('the select column is neither rendered nor pinned when no action is permitted', () => {
  expect(serviceColumns(false).map(columnId)).not.toContain('select')
  expect(buildHostServicesColumnPinning({ includeSelect: false }).left).toEqual(['state', 'name'])
})

test('the hidden columns stay on offer in the picker', () => {
  expect(makeService().toggleableColumns.map((column) => column.id)).toEqual(
    expect.arrayContaining(['labels', 'tags', 'contacts', 'contact_groups', 'groups'])
  )
})

test('the select column adds itself without disturbing the other columns', () => {
  // Two users of the same table, one permitted to act on a selection and one not,
  // must see tables that differ in nothing but that column.
  const ids = (includeSelect: boolean) =>
    serviceColumns(includeSelect).map((column) => columnId(column as ColumnDef<never>))

  expect(ids(true).filter((id) => id !== 'select')).toEqual(ids(false))
  expect(schemaOf(true).hideable).toEqual(schemaOf(false).hideable)
  expect(schemaOf(true).sortable).toEqual(schemaOf(false).sortable)
})

test('the select column is never on offer in the picker', () => {
  expect(schemaOf(true).hideable).not.toContain('select')
  expect(makeService().toggleableColumns.map((column) => column.id)).not.toContain('select')
})

test('the contacts column keeps its substring search', () => {
  const contactsColumn = serviceColumns().find((column) => columnId(column) === 'contacts')

  expect(contactsColumn?.meta?.filter).toEqual({ type: 'string-input', field: 'contacts' })
})

function nameColumn(columns: ColumnDef<HostServiceEntry>[]): ColumnDef<HostServiceEntry> {
  return columns.find((column) => columnId(column) === 'name')!
}

test('the service name keeps its cap while the summary takes the spare width', () => {
  const columns = uncapNameWithoutSummary(serviceColumns(), {})

  expect(nameColumn(columns).maxSize).toBe(350)
})

test('the service name takes the spare width once the summary is hidden', () => {
  const columns = uncapNameWithoutSummary(serviceColumns(), { summary: false })

  expect(nameColumn(columns).maxSize).toBeUndefined()
  expect(nameColumn(columns).minSize).toBe(150)
})

function actionsSize(inlineActions: number): number {
  return useHostServicesColumns({ includeSelect: true, inlineActions }).find(
    (column) => columnId(column) === 'actions'
  )!.minSize!
}

test('the actions column widens by one button width per inline action', () => {
  expect(actionsSize(3) - actionsSize(2)).toBe(actionsSize(2) - actionsSize(1))
  expect(actionsSize(2)).toBeGreaterThan(actionsSize(1))
})

test('the actions column keeps its header readable without inline actions', () => {
  expect(actionsSize(0)).toBe(ACTIONS_HEADER_WIDTH)
})

test('last state change comes before last check, matching the legacy view', () => {
  const ids = serviceColumns().map((column) => columnId(column as ColumnDef<never>))
  expect(ids.indexOf('last_state_change')).toBeLessThan(ids.indexOf('last_check'))
})

test('the export carries every data column of the table in table order', () => {
  const dataColumns = serviceColumns()
    .map(columnId)
    .filter((id) => id !== 'select' && id !== 'actions')

  expect(RowExport.shownColumns(serviceColumns(), {}, ServiceExport.isColumn)).toEqual(dataColumns)
})

test('shows in its column filters the conditions the shared schema names', () => {
  const shown = serviceColumns().flatMap((column) =>
    column.meta?.filter ? listShownConditions(column.meta.filter) : []
  )

  expect([...new Set(shown)].sort()).toEqual(Object.keys(HOST_SERVICES_FILTER_CONDITIONS).sort())
})
