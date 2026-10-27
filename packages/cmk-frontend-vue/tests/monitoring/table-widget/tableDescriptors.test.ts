/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { columnId } from '@/monitoring/shared/tableState/schema'
import {
  HostsTableDescriptor,
  ServicesTableDescriptor
} from '@/monitoring/table-widget/tableDescriptors'

const HOST_TABLE_COLUMNS = [
  'state',
  'modes',
  'name',
  'alias',
  'address',
  'folder',
  'site_id',
  'last_check',
  'last_state_change',
  'labels',
  'tags',
  'contacts',
  'contact_groups',
  'num_services',
  'num_services_ok',
  'num_services_warn',
  'num_services_crit',
  'num_services_unknown',
  'num_services_pending',
  'customer'
]

const SORTABLE_COLUMNS = [
  'name',
  'alias',
  'address',
  'state',
  'num_services',
  'num_services_ok',
  'num_services_warn',
  'num_services_crit',
  'num_services_unknown',
  'num_services_pending',
  'folder',
  'site_id',
  'last_check',
  'last_state_change'
]

describe('HostsTableDescriptor', () => {
  it('offers exactly the columns the backend offers for the hosts table', () => {
    const offered = new HostsTableDescriptor().catalog().map((column) => column.id)

    expect(offered).toEqual(HOST_TABLE_COLUMNS)
  })

  it('renders every column the backend offers for the hosts table', () => {
    const rendered = new HostsTableDescriptor().columns(HOST_TABLE_COLUMNS).map(columnId)

    expect(rendered).toEqual(HOST_TABLE_COLUMNS)
  })

  it('offers sorting on exactly the columns the backend can sort', () => {
    const sortable = new HostsTableDescriptor()
      .columns(HOST_TABLE_COLUMNS)
      .filter((column) => column.enableSorting !== false)
      .map(columnId)

    expect(sortable.sort()).toEqual([...SORTABLE_COLUMNS].sort())
  })
})

const SERVICE_TABLE_COLUMNS = [
  'state',
  'modes',
  'host_name',
  'name',
  'summary',
  'last_state_change',
  'last_check',
  'labels',
  'tags',
  'contacts',
  'contact_groups',
  'groups',
  'perfometer'
]

const SORTABLE_SERVICE_COLUMNS = [
  'host_name',
  'state',
  'name',
  'summary',
  'last_state_change',
  'last_check'
]

describe('ServicesTableDescriptor', () => {
  it('offers exactly the columns the backend offers for the services table', () => {
    const offered = new ServicesTableDescriptor().catalog().map((column) => column.id)

    expect(offered).toEqual(SERVICE_TABLE_COLUMNS)
  })

  it('shows the less common columns only on request', () => {
    const shown = new ServicesTableDescriptor()
      .catalog()
      .filter((column) => column.shownByDefault)
      .map((column) => column.id)

    expect(shown).toEqual(['state', 'modes', 'host_name', 'name', 'summary'])
  })

  it('renders every column the backend offers for the services table', () => {
    const rendered = new ServicesTableDescriptor().columns(SERVICE_TABLE_COLUMNS).map(columnId)

    expect(rendered).toEqual(SERVICE_TABLE_COLUMNS)
  })

  it('offers sorting on exactly the columns the backend can sort', () => {
    const sortable = new ServicesTableDescriptor()
      .columns(SERVICE_TABLE_COLUMNS)
      .filter((column) => column.enableSorting !== false)
      .map(columnId)

    expect(sortable.sort()).toEqual([...SORTABLE_SERVICE_COLUMNS].sort())
  })
})
