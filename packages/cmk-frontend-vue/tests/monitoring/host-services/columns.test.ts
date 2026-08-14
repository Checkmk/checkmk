/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { useHostServicesColumns, visibleServiceFields } from '@/monitoring/host-services/columns'
import type { HostServiceEntry } from '@/monitoring/shared/api/types'
import {
  MonitoringService,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import { makeKeyShortcutService, makeResponse } from '../shared/services/testHelpers'

class ServiceColumnService extends MonitoringService<HostServiceEntry> {
  constructor(columns: ColumnDef<HostServiceEntry>[], shortCuts: KeyShortcutService) {
    super('host-services-columns', shortCuts, { columns })
  }

  protected fetchBatch(): Promise<PagedResponse<HostServiceEntry>> {
    return Promise.resolve(makeResponse([], 0, 0))
  }
}

function makeService() {
  const service = new ServiceColumnService(useHostServicesColumns(), makeKeyShortcutService())
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

test('the hidden columns stay on offer in the picker', () => {
  expect(makeService().toggleableColumns.map((column) => column.id)).toEqual(
    expect.arrayContaining(['labels', 'tags', 'contacts', 'contact_groups'])
  )
})
