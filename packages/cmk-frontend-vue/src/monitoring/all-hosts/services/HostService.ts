/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import type { HostApi } from '@/monitoring/shared/api/hosts'
import type { HostEntry, HostOptionalField } from '@/monitoring/shared/api/types'
import { RowExport } from '@/monitoring/shared/export/rowExport'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import { visibleHostFields } from '../columns'
import { HostExport, type HostExportColumn } from '../export/hostExport'

export interface HostServiceOptions extends MonitoringServiceOptions<HostEntry> {
  /** Fields read on every fetch, whichever columns are shown, for what a row offers. */
  rowFields?: readonly HostOptionalField[]
}

export class HostService extends MonitoringService<HostEntry> {
  private readonly rowFields: readonly HostOptionalField[]
  private readonly columns: readonly ColumnDef<HostEntry>[]

  constructor(
    private readonly api: Pick<HostApi, 'fetchHosts'>,
    shortCutService: KeyShortcutService,
    options: HostServiceOptions = {}
  ) {
    super('host-service', shortCutService, options)
    this.rowFields = options.rowFields ?? []
    this.columns = options.columns ?? []
  }

  async export(): Promise<HostExport> {
    const hosts = await this.loadedItems()
    return new HostExport(this.exportColumns(), hosts)
  }

  exportColumns(): HostExportColumn[] {
    return RowExport.shownColumns(this.columns, this.columnVisibility.value, HostExport.isColumn)
  }

  protected async fetchBatch(signal: AbortSignal): Promise<PagedResponse<HostEntry>> {
    const response = await this.api.fetchHosts(
      {
        limit: this.requestedLimit.value,
        sort: this.sortState.value,
        searchQuery: this.appliedSearchQuery.value,
        filter: this.filterState.value,
        fields: [
          ...visibleHostFields(this.columnVisibility.value, this.hideableColumnIds),
          ...this.rowFields
        ]
      },
      signal
    )
    return { items: response.hosts, meta: response.meta }
  }
}
