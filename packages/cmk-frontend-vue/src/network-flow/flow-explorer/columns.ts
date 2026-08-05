/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnPinningState } from '@tanstack/vue-table'
import usei18n from 'cmk-ui-library/lib/i18n'

import { columnId } from '@/monitoring/shared/services/MonitoringService'

import type { FlowEntry, FlowSortColumn } from './api/flows'

/**
 * The columns frozen to the left edge of the table once it has to scroll
 * horizontally: when reading a wide row, the time and who sent it are what
 * identify it.
 */
export function buildFlowColumnPinning(): ColumnPinningState {
  return { left: ['first_seen', 'source_ip'] }
}

export interface FlowColumnOptions {
  /**
   * Whether to offer the header funnels. They render a filter's own definition,
   * which the page has to fetch first, so they are attached only once those
   * definitions are in - a funnel opened before then would have nothing to show.
   */
  withFilters: boolean
}

/**
 * The columns of the flow listing.
 *
 * The sortable ones are exactly the endpoint's sort columns. Protocol,
 * application, direction and the last-seen/out-interface columns are not
 * sortable: their values are either resolved to names in Python - so the
 * database could only order them by numeric id, which reads as an arbitrary
 * order - or not a stored sort key at all. Columns carrying `hidden` are off
 * until a user picks them in the column picker.
 */
export function buildFlowColumns({ withFilters }: FlowColumnOptions): ColumnDef<FlowEntry>[] {
  return _buildFlowColumns().map((column) => {
    const id = columnId(column)
    const filterId = withFilters && id !== undefined ? COLUMN_FILTERS[id] : undefined
    return filterId === undefined
      ? column
      : { ...column, meta: { ...column.meta, filter: { type: 'visual-filter', filterId } } }
  })
}

function _buildFlowColumns(): ColumnDef<FlowEntry>[] {
  const { _t } = usei18n()

  return [
    {
      accessorKey: 'first_seen',
      header: _t('First seen'),
      // Newest first is both the useful default and the order the table is
      // stored in, so it is also the cheapest.
      sortDescFirst: true,
      enableHiding: false,
      minSize: 95,
      maxSize: 120
    },
    {
      accessorKey: 'source_ip',
      header: _t('Source'),
      enableHiding: false,
      minSize: 180,
      meta: { headerTitle: _t('Source address, port and autonomous system') }
    },
    {
      accessorKey: 'destination_ip',
      header: _t('Destination'),
      enableHiding: false,
      minSize: 180,
      meta: { headerTitle: _t('Destination address, port and autonomous system') }
    },
    {
      accessorKey: 'protocol_name',
      header: _t('Protocol'),
      enableSorting: false,
      minSize: 85,
      maxSize: 110,
      meta: { headerTitle: _t('Layer-4 protocol') }
    },
    {
      accessorKey: 'application',
      header: _t('Application'),
      enableSorting: false,
      minSize: 120
    },
    {
      accessorKey: 'total_bytes',
      header: _t('Bytes'),
      sortDescFirst: true,
      minSize: 80,
      maxSize: 110,
      meta: { justify: 'right' }
    },
    {
      accessorKey: 'packets',
      header: _t('Packets'),
      sortDescFirst: true,
      minSize: 80,
      maxSize: 110,
      meta: { justify: 'right' }
    },
    {
      accessorKey: 'direction',
      header: _t('Direction'),
      enableSorting: false,
      minSize: 90,
      maxSize: 120,
      meta: {
        headerHelp: _t(
          'Where the flow sits relative to the local network: ingress (remote to local), ' +
            'egress (local to remote), internal (local to local) or external (remote to remote).'
        )
      }
    },
    {
      accessorKey: 'input_interface',
      header: _t('Interface'),
      minSize: 90,
      maxSize: 130,
      meta: {
        justify: 'right',
        headerHelp: _t(
          'The ifIndex the flow entered on. Resolving it to a Checkmk interface name is not ' +
            'implemented yet.'
        )
      }
    },
    {
      accessorKey: 'output_interface',
      header: _t('Out interface'),
      enableSorting: false,
      minSize: 90,
      maxSize: 130,
      // Off by default: the input interface identifies where a flow was seen, and
      // both columns together crowd the row.
      meta: { justify: 'right', hidden: true }
    },
    {
      accessorKey: 'last_seen',
      header: _t('Last seen'),
      enableSorting: false,
      minSize: 80,
      maxSize: 110,
      meta: { hidden: true }
    }
  ]
}

/**
 * Column id -> the Network flow filter its header funnel edits.
 *
 * Every filter the page offers is reached from the column it constrains, so
 * there is no filter bar. The time filter windows FIRST_SEEN, which is what the
 * First seen column shows.
 *
 * The Network flow "Host" filter has no entry: it matches either side of a flow, so
 * on this page it is split into the per-side Source and Destination filters. It
 * stays registered for the dashboards, and a URL that carries it keeps working -
 * the funnels just do not offer it.
 */
export const COLUMN_FILTERS: Readonly<Record<string, string>> = {
  first_seen: 'network_flow_time',
  source_ip: 'network_flow_source',
  destination_ip: 'network_flow_destination',
  application: 'network_flow_application',
  protocol_name: 'network_flow_protocol',
  total_bytes: 'network_flow_min_bytes'
}

/**
 * Column id -> the endpoint's sort column. Only the sortable columns appear; the
 * table's own ids differ from the API's where the column renders more than the
 * one field it is keyed by.
 */
export const SORT_COLUMNS: Readonly<Record<string, FlowSortColumn>> = {
  first_seen: 'time',
  source_ip: 'source_ip',
  destination_ip: 'destination_ip',
  total_bytes: 'bytes',
  packets: 'packets',
  input_interface: 'input_interface'
}
