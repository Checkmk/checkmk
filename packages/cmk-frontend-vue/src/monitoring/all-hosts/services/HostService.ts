/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import type { HostEntry } from '@/monitoring/shared/api/types'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import type { HostApi } from '../api/hosts'
import { visibleHostFields } from '../columns'

export class HostService extends MonitoringService<HostEntry> {
  constructor(
    private readonly api: Pick<HostApi, 'fetchHosts'>,
    shortCutService: KeyShortcutService,
    options: MonitoringServiceOptions<HostEntry> = {}
  ) {
    super('host-service', shortCutService, options)
  }

  protected async fetchBatch(signal: AbortSignal): Promise<PagedResponse<HostEntry>> {
    const response = await this.api.fetchHosts(
      {
        limit: this.requestedLimit.value,
        sort: this.sortState.value,
        searchQuery: this.appliedSearchQuery.value,
        filter: this.filterState.value,
        fields: visibleHostFields(this.columnVisibility.value)
      },
      signal
    )
    return { items: response.hosts, meta: response.meta }
  }
}
