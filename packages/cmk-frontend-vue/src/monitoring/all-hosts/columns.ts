/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnPinningState } from '@tanstack/vue-table'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostEntry, HostState } from '@/monitoring/shared/api/types'
import type {
  BooleanGroupFilter,
  CheckboxListFilter,
  NumericFilter,
  StringInputFilter
} from '@/monitoring/shared/components/filter/types'

export interface HostColumnOptions {
  /** Whether to render the row-action column, which needs permitted actions. */
  includeActions: boolean
}

/**
 * The columns frozen to the edges of the table once it has to scroll
 * horizontally.
 */
export function buildHostColumnPinning({ includeActions }: HostColumnOptions): ColumnPinningState {
  return {
    left: ['select', 'state', 'modes', 'name'],
    ...(includeActions ? { right: ['actions'] } : {})
  }
}

/**
 * The columns of the All Hosts table.
 *
 * `enableHiding: false` keeps them out of the column picker.
 * Columns carrying `hidden` are off until a user picks them, which defines the
 * set shown on first use.
 */
export function buildHostColumns({ includeActions }: HostColumnOptions): ColumnDef<HostEntry>[] {
  const { _t } = usei18n()

  const stateFilter: CheckboxListFilter<'state'> = {
    type: 'checkbox-list',
    field: 'state',
    options: [
      { value: 'UP', title: _t('UP') },
      { value: 'DOWN', title: _t('DOWN') },
      { value: 'UNREACHABLE', title: _t('UNREACH') }
    ] satisfies { value: HostState; title: string }[]
  }

  const nameFilter: StringInputFilter<'name'> = {
    type: 'string-input',
    field: 'name'
  }

  const addressFilter: StringInputFilter<'address'> = {
    type: 'string-input',
    field: 'address'
  }

  const totalServicesFilter: NumericFilter<'num_services'> = {
    type: 'numeric',
    field: 'num_services'
  }

  const okServicesFilter: NumericFilter<'num_services_ok'> = {
    type: 'numeric',
    field: 'num_services_ok'
  }

  const warnServicesFilter: NumericFilter<'num_services_warn'> = {
    type: 'numeric',
    field: 'num_services_warn'
  }

  const critServicesFilter: NumericFilter<'num_services_crit'> = {
    type: 'numeric',
    field: 'num_services_crit'
  }

  const unknownServicesFilter: NumericFilter<'num_services_unknown'> = {
    type: 'numeric',
    field: 'num_services_unknown'
  }

  const pendingServicesFilter: NumericFilter<'num_services_pending'> = {
    type: 'numeric',
    field: 'num_services_pending'
  }

  const modesFilter: BooleanGroupFilter<'in_downtime' | 'acknowledged'> = {
    type: 'boolean-group',
    groups: [
      { field: 'in_downtime', title: _t('In downtime') },
      { field: 'acknowledged', title: _t('Acknowledged') }
    ]
  }

  return [
    {
      id: 'select',
      header: '',
      enableSorting: false,
      minSize: 36,
      maxSize: 36,
      meta: { selectColumn: true, justify: 'center' }
    },
    {
      accessorKey: 'state',
      header: _t('State'),
      sortDescFirst: true,
      enableHiding: false,
      minSize: 74,
      maxSize: 100,
      meta: { filter: stateFilter }
    },
    {
      accessorKey: 'modes',
      header: _t('Mode'),
      enableSorting: false,
      enableHiding: false,
      minSize: 80,
      maxSize: 80,
      meta: { justify: 'left', filter: modesFilter }
    },
    {
      accessorKey: 'name',
      header: _t('Host'),
      sortDescFirst: false,
      enableHiding: false,
      minSize: 150,
      meta: { filter: nameFilter }
    },
    {
      accessorKey: 'address',
      header: _t('IP address'),
      sortDescFirst: false,
      minSize: 100,
      maxSize: 300,
      meta: { filter: addressFilter }
    },
    {
      accessorKey: 'num_services',
      header: _t('All services'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: totalServicesFilter,
        headerTitle: _t('Total number of services')
      },
      minSize: 70,
      maxSize: 130
    },
    {
      accessorKey: 'num_services_ok',
      header: _t('OK'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: okServicesFilter,
        headerTitle: _t('Number of services in OK state')
      },
      minSize: 70,
      maxSize: 70
    },
    {
      accessorKey: 'num_services_warn',
      header: _t('Wa'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: warnServicesFilter,
        headerTitle: _t('Number of services in warning state')
      },
      minSize: 70,
      maxSize: 70
    },
    {
      accessorKey: 'num_services_crit',
      header: _t('Cr'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: critServicesFilter,
        headerTitle: _t('Number of services in critical state')
      },
      minSize: 70,
      maxSize: 70
    },
    {
      accessorKey: 'num_services_unknown',
      header: _t('Un'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: unknownServicesFilter,
        headerTitle: _t('Number of services in unknown state')
      },
      minSize: 70,
      maxSize: 70
    },
    {
      accessorKey: 'num_services_pending',
      header: _t('Pd'),
      sortDescFirst: true,
      meta: {
        justify: 'right',
        filter: pendingServicesFilter,
        headerTitle: _t('Number of services in pending state')
      },
      minSize: 70,
      maxSize: 70
    },
    ...(includeActions
      ? [
          {
            id: 'actions',
            header: _t('Actions'),
            enableSorting: false,
            enableHiding: false,
            minSize: 75,
            maxSize: 75,
            meta: { justify: 'right' }
          } satisfies ColumnDef<HostEntry>
        ]
      : [])
  ]
}
