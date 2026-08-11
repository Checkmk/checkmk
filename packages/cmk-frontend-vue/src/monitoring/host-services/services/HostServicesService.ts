/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import type { HostRef, HostServiceEntry } from '@/monitoring/shared/api/types'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import type { HostServicesApi } from '../api/services'
import { visibleServiceFields } from '../columns'

export class HostServicesService extends MonitoringService<HostServiceEntry> {
  constructor(
    private readonly api: Pick<HostServicesApi, 'fetchServices'>,
    private readonly host: HostRef,
    shortCutService: KeyShortcutService,
    options: MonitoringServiceOptions<HostServiceEntry> = {}
  ) {
    super('host-services-service', shortCutService, options)
  }

  protected async fetchBatch(signal: AbortSignal): Promise<PagedResponse<HostServiceEntry>> {
    const response = await this.api.fetchServices(
      this.host,
      {
        limit: this.requestedLimit.value,
        sort: this.sortState.value,
        searchQuery: this.searchQuery.value,
        filter: this.filterState.value,
        fields: visibleServiceFields(this.columnVisibility.value)
      },
      signal
    )
    return { items: response.services, meta: response.meta }
  }
}
