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

export interface HostApi {
  fetchHosts(): Promise<PagedResponse<HostEntry>>
}

export class HostService extends MonitoringService<HostEntry> {
  private readonly api: HostApi

  constructor(api: HostApi) {
    super()
    this.api = api
  }

  protected fetchBatch(): Promise<PagedResponse<HostEntry>> {
    return this.api.fetchHosts()
  }
}
