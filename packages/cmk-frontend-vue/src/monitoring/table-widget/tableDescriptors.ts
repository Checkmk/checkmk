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
import type { HostEntry } from '@/monitoring/shared/api/types'
import { columnId } from '@/monitoring/shared/tableState/schema'

export type MonitoringTableName = components['schemas']['MonitoringTableContent']['table']

export interface MonitoringTableRows {
  hosts: HostEntry
}

export interface MonitoringTableColumn {
  id: string
  title: string
  sortable: boolean
  shownByDefault: boolean
}

export abstract class MonitoringTableDescriptor<T> {
  abstract readonly rowComponent: Component

  /** The columns the backend offers for this table, in the order the row renders them. */
  abstract readonly columnIds: readonly string[]

  protected abstract allColumns(): ColumnDef<T>[]

  abstract rowKey(row: T): string

  abstract truncatedHint(shown: number, matched: number): string

  catalog(): MonitoringTableColumn[] {
    const byId = new Map(this.allColumns().map((column) => [columnId(column), column]))
    return this.columnIds.flatMap((id) => {
      const column = byId.get(id)
      return column
        ? [
            {
              id,
              title: typeof column.header === 'string' ? column.header : id,
              sortable: column.enableSorting !== false,
              shownByDefault: !column.meta?.hidden
            }
          ]
        : []
    })
  }

  columns(ids: readonly string[]): ColumnDef<T>[] {
    const byId = new Map(this.allColumns().map((column) => [columnId(column), column]))
    return ids.flatMap((id) => {
      const column = byId.get(id)
      return column ? [{ ...column, enableColumnFilter: false, enableHiding: false }] : []
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
