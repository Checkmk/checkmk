/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { Component } from 'vue'

import { buildHostColumns } from '@/monitoring/all-hosts/columns'
import HostRow from '@/monitoring/all-hosts/components/HostRow.vue'
import { useAllServicesColumns } from '@/monitoring/all-services/columns'
import HostServicesRow from '@/monitoring/host-services/components/HostServicesRow.vue'
import type { HostEntry, ServiceEntry } from '@/monitoring/shared/api/types'
import { columnId } from '@/monitoring/shared/tableState/schema'

export type MonitoringTableName = components['schemas']['MonitoringTableContent']['table']

export interface MonitoringTableRows {
  hosts: HostEntry
  services: ServiceEntry
}

export interface MonitoringTableColumn {
  id: string
  title: string
  sortable: boolean
  shownByDefault: boolean
}

export abstract class MonitoringTableDescriptor<T> {
  abstract readonly rowComponent: Component

  /** The columns the backend offers for this table. */
  abstract readonly columnIds: readonly string[]

  /** The columns of the full page, in the order the row renders them. */
  protected abstract allColumns(): ColumnDef<T>[]

  abstract rowKey(row: T): string

  abstract truncatedHint(shown: number, matched: number): string

  catalog(): MonitoringTableColumn[] {
    return this.inRowOrder(this.columnIds).map(([id, column]) => ({
      id,
      title: typeof column.header === 'string' ? column.header : id,
      sortable: column.enableSorting !== false,
      shownByDefault: !column.meta?.hidden
    }))
  }

  // The row draws its cells in a fixed order, so the headers follow it, whatever order `ids` has.
  columns(ids: readonly string[]): ColumnDef<T>[] {
    return this.inRowOrder(ids).map(([, column]) => ({
      ...column,
      enableColumnFilter: false,
      enableHiding: false
    }))
  }

  private inRowOrder(ids: readonly string[]): [string, ColumnDef<T>][] {
    const wanted = new Set(ids)
    return this.allColumns().flatMap<[string, ColumnDef<T>]>((column) => {
      const id = columnId(column)
      return id !== undefined && wanted.has(id) ? [[id, column]] : []
    })
  }
}

export class HostsTableDescriptor extends MonitoringTableDescriptor<HostEntry> {
  readonly rowComponent: Component = HostRow

  readonly columnIds = [
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

  protected allColumns(): ColumnDef<HostEntry>[] {
    return buildHostColumns({
      includeSelect: false,
      showCustomer: true,
      sites: [],
      showRelations: false
    })
  }

  rowKey(row: HostEntry): string {
    return `${row.site_id}:${row.name}`
  }

  truncatedHint(shown: number, matched: number): string {
    const { _t } = usei18n()
    return _t('Showing %{shown} of %{matched} hosts', {
      shown: String(shown),
      matched: String(matched)
    })
  }
}

export class ServicesTableDescriptor extends MonitoringTableDescriptor<ServiceEntry> {
  readonly rowComponent: Component = HostServicesRow

  readonly columnIds = [
    'state',
    'modes',
    'name',
    'summary',
    'host_name',
    'last_state_change',
    'last_check',
    'labels',
    'tags',
    'contacts',
    'contact_groups',
    'groups',
    'perfometer'
  ]

  protected allColumns(): ColumnDef<ServiceEntry>[] {
    return useAllServicesColumns({ sites: [], includeSelect: false }).filter(
      (column) => columnId(column) !== 'actions'
    )
  }

  rowKey(row: ServiceEntry): string {
    return `${row.site_id}:${row.host_name}:${row.name}`
  }

  truncatedHint(shown: number, matched: number): string {
    const { _t } = usei18n()
    return _t('Showing %{shown} of %{matched} services', {
      shown: String(shown),
      matched: String(matched)
    })
  }
}
