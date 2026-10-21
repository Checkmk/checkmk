/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  defaultMonitoringTableContent,
  filtersForeignTo
} from '@/dashboard/components/Wizard/wizards/monitoring-table/monitoringTables'

describe('defaultMonitoringTableContent', () => {
  it('shows the columns the All hosts page shows by default, unsorted, up to 1000 rows', () => {
    expect(defaultMonitoringTableContent('hosts')).toEqual({
      type: 'monitoring_table',
      table: 'hosts',
      columns: [
        'state',
        'modes',
        'name',
        'address',
        'num_services',
        'num_services_ok',
        'num_services_warn',
        'num_services_crit',
        'num_services_unknown',
        'num_services_pending'
      ],
      sort: [],
      limit: 1000
    })
  })
})

describe('filtersForeignTo', () => {
  it('drops the service filters of a widget switched to All hosts', () => {
    const infos: Record<string, string> = { hostregex: 'host', serviceregex: 'service' }

    expect(filtersForeignTo('hosts', ['hostregex', 'serviceregex'], (id) => infos[id])).toEqual([
      'serviceregex'
    ])
  })
})
