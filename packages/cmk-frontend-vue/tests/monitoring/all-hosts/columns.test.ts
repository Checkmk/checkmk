/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import {
  buildHostColumnPinning,
  buildHostColumns,
  visibleHostFields
} from '@/monitoring/all-hosts/columns'
import type { HostEntry } from '@/monitoring/shared/api/types'
import {
  MonitoringService,
  type PagedResponse,
  columnId
} from '@/monitoring/shared/services/MonitoringService'

import { makeKeyShortcutService, makeResponse } from '../shared/services/testHelpers'

class HostColumnService extends MonitoringService<HostEntry> {
  constructor(columns: ColumnDef<HostEntry>[], shortCuts: KeyShortcutService) {
    super('all-hosts-columns', shortCuts, { columns })
  }

  protected fetchBatch(): Promise<PagedResponse<HostEntry>> {
    return Promise.resolve(makeResponse([], 0, 0))
  }
}

function makeService() {
  const service = new HostColumnService(
    buildHostColumns({ includeActions: true }),
    makeKeyShortcutService()
  )
  service.stopPolling()
  return service
}

function columnIds(includeActions = true): (string | undefined)[] {
  return buildHostColumns({ includeActions }).map(columnId)
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
    { id: 'address', label: 'IP address' },
    { id: 'num_services', label: 'All services' },
    { id: 'num_services_ok', label: 'OK' },
    { id: 'num_services_warn', label: 'Wa' },
    { id: 'num_services_crit', label: 'Cr' },
    { id: 'num_services_unknown', label: 'Un' },
    { id: 'num_services_pending', label: 'Pd' }
  ])
})

test('every offered column is shown on first use', () => {
  const service = makeService()

  expect(service.defaultColumnVisibility).toEqual({})
  expect(service.columnVisibility.value).toEqual({})
})

test('the fixed columns keep their position around the optional ones', () => {
  expect(columnIds()).toEqual([
    'select',
    'state',
    'modes',
    'name',
    'address',
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
  expect(visibleHostFields({})).toEqual(makeService().toggleableColumns.map((column) => column.id))
})

test('a hidden column stops asking for its field', () => {
  const fields = visibleHostFields({ address: false, num_services_pending: false })

  expect(fields).not.toContain('address')
  expect(fields).not.toContain('num_services_pending')
  expect(fields).toContain('num_services')
})

test('the fields of the fixed columns are never asked for, the API always sending them', () => {
  // Only what the API treats as optional can be requested; 'state', 'name' and
  // the modes come with every host either way.
  expect(visibleHostFields({})).not.toContain('state')
  expect(visibleHostFields({})).not.toContain('name')
  expect(visibleHostFields({})).not.toContain('modes')
})

test('the actions column is neither rendered nor pinned when no row action is permitted', () => {
  expect(columnIds(false)).not.toContain('actions')
  expect(buildHostColumnPinning({ includeActions: false }).right).toBeUndefined()
})
