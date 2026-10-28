/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { EventEntry } from './api'

/** What the History tab lists the events of: a host, or a single service. */
export type HistorySubject = 'host' | 'service'

/**
 * The columns of the History tab.
 *
 * The tab is read-only - the way to a filtered or sorted history is its link to the full
 * history view - so every column turns sorting, hiding and filtering off and carries no
 * `meta.filter`. That keeps `MonitoringTableHeader` from rendering any affordance for
 * them.
 *
 * The service column only makes sense for a host, whose events include those of its
 * services; a service's own history would repeat its name on every row.
 */
export function buildHistoryColumns(subject: HistorySubject): ColumnDef<EventEntry>[] {
  const { _t } = usei18n()

  const columns: ColumnDef<EventEntry>[] = [
    {
      id: 'icon',
      header: '',
      minSize: 30,
      maxSize: 30
    },
    {
      accessorKey: 'time',
      header: _t('Time'),
      minSize: 140,
      maxSize: 140
    },
    {
      accessorKey: 'event',
      header: _t('Event'),
      minSize: 120,
      maxSize: 200
    }
  ]

  if (subject === 'host') {
    columns.push({
      accessorKey: 'service_name',
      header: _t('Service'),
      minSize: 100,
      maxSize: 200
    })
  }

  columns.push(
    {
      accessorKey: 'state_info',
      header: _t('State info'),
      minSize: 100,
      maxSize: 180
    },
    {
      accessorKey: 'plugin_output',
      header: _t('Summary'),
      minSize: 150
    }
  )

  return columns.map((column) => ({
    ...column,
    enableSorting: false,
    enableHiding: false,
    enableColumnFilter: false
  }))
}
