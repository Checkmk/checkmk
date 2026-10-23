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

export abstract class MonitoringTableDescriptor<T> {
  abstract readonly rowComponent: Component

  protected abstract allColumns(): ColumnDef<T>[]

  abstract rowKey(row: T): string

  abstract truncatedHint(shown: number, matched: number): string

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
