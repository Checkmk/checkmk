/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { type Ref, shallowRef } from 'vue'

import type { HostApi } from '@/monitoring/shared/api/hosts'
import type {
  HostEntry,
  HostOptionalField,
  HostRef,
  HostServiceEntry
} from '@/monitoring/shared/api/types'
import { RowExport } from '@/monitoring/shared/export/rowExport'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import type { HostServicesApi, HostServicesQueryParams } from '../api/services'
import { visibleServiceFields } from '../columns'
import { ServiceExport, type ServiceExportColumn } from '../export/serviceExport'

export interface HostServicesServiceOptions extends MonitoringServiceOptions<HostServiceEntry> {
  /** Fields read on the host of the page on every fetch, for what its header and slide-in offer. */
  hostFields?: readonly HostOptionalField[]
}

export class HostServicesService extends MonitoringService<HostServiceEntry> {
  readonly hostEntry: Ref<HostEntry | null> = shallowRef<HostEntry | null>(null)
  private readonly hostFields: readonly HostOptionalField[]
  private readonly columns: readonly ColumnDef<HostServiceEntry>[]

  constructor(
    private readonly api: Pick<HostServicesApi, 'fetchServices'>,
    private readonly hostApi: Pick<HostApi, 'fetchHost'>,
    private readonly host: HostRef,
    shortCutService: KeyShortcutService,
    options: HostServicesServiceOptions = {}
  ) {
    super('host-services-service', shortCutService, options)
    this.hostFields = options.hostFields ?? []
    this.columns = options.columns ?? []
  }

  async export(): Promise<ServiceExport> {
    const services = await this.loadedItems()
    return new ServiceExport(this.host.name, this.exportColumns(), services)
  }

  exportColumns(): ServiceExportColumn[] {
    return RowExport.shownColumns(this.columns, this.columnVisibility.value, ServiceExport.isColumn)
  }

  /** What the listing asks the endpoint for, whatever fields its rows read. */
  listingParams(): HostServicesQueryParams {
    return {
      limit: this.requestedLimit.value,
      sort: this.sortState.value,
      searchQuery: this.appliedSearchQuery.value,
      filter: this.filterState.value
    }
  }

  protected async fetchBatch(signal: AbortSignal): Promise<PagedResponse<HostServiceEntry>> {
    const [response, hostEntry] = await Promise.all([
      this.api.fetchServices(
        this.host,
        {
          ...this.listingParams(),
          fields: visibleServiceFields(this.columnVisibility.value)
        },
        signal
      ),
      this.hostApi.fetchHost(
        this.host,
        signal,
        this.hostFields.length > 0 ? this.hostFields : undefined
      )
    ])
    this.hostEntry.value = hostEntry
    return { items: response.services, meta: response.meta }
  }
}
