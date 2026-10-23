/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { columnId } from '@/monitoring/shared/tableState/schema'
import { HostsTableDescriptor } from '@/monitoring/table-widget/tableDescriptors'

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
