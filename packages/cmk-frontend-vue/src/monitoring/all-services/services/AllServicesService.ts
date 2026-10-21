/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import { visibleServiceFields } from '@/monitoring/host-services/columns'
import { ServiceWithHostExport } from '@/monitoring/host-services/export/serviceExport'
import type { ServiceEntry } from '@/monitoring/shared/api/types'
import { RowExport } from '@/monitoring/shared/export/rowExport'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import type { AllServicesApi } from '../api/services'

export class AllServicesService extends MonitoringService<ServiceEntry> {
  private readonly columns: readonly ColumnDef<ServiceEntry>[]

  constructor(
    private readonly api: Pick<AllServicesApi, 'fetchServices'>,
    shortCutService: KeyShortcutService,
    options: MonitoringServiceOptions<ServiceEntry> = {}
  ) {
    super('all-services-service', shortCutService, options)
    this.columns = options.columns ?? []
  }

  async export(): Promise<ServiceWithHostExport> {
    const services = await this.loadedItems()
    return new ServiceWithHostExport(
      'all',
      RowExport.shownColumns(
        this.columns,
        this.columnVisibility.value,
        ServiceWithHostExport.isColumn
      ),
      services
    )
  }

  protected async fetchBatch(signal: AbortSignal): Promise<PagedResponse<ServiceEntry>> {
    const response = await this.api.fetchServices(
      {
        limit: this.requestedLimit.value,
        sort: this.sortState.value,
        searchQuery: this.appliedSearchQuery.value,
        filter: this.filterState.value,
        fields: visibleServiceFields(this.columnVisibility.value)
      },
      signal
    )
    return { items: response.services, meta: response.meta }
  }
}
