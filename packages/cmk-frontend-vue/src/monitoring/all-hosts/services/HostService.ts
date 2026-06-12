/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { HostEntry } from '@/monitoring/shared/api/types'
import {
  MonitoringService,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import type { HostApi } from '../api/hosts'

export class HostService extends MonitoringService<HostEntry> {
  constructor(
    private readonly api: HostApi,
    pollIntervalMs?: number
  ) {
    super(pollIntervalMs)
  }

  protected async fetchBatch(): Promise<PagedResponse<HostEntry>> {
    const response = await this.api.fetchHosts({
      sort: this.sortState.value,
      searchQuery: this.searchQuery.value,
      filter: this.filterState.value
    })
    return { items: response.hosts, meta: response.meta }
  }
}
