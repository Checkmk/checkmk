/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { MonitoringApi, type MonitoringQueryParams } from '@/monitoring/shared/api/MonitoringApi'
import type { HostRef, HostServicesResponse } from '@/monitoring/shared/api/types'

export class HostServicesApi extends MonitoringApi {
  public async fetchServices(
    host: HostRef,
    params: MonitoringQueryParams = {},
    signal?: AbortSignal
  ): Promise<HostServicesResponse> {
    return unwrap(
      await client.POST('/monitor/hosts/{hostname}/services', {
        params: {
          path: { hostname: host.name },
          query: { site_id: host.site_id },
          header: { 'Content-Type': 'application/json' }
        },
        body: this.buildRequestBody(params),
        ...(signal && { signal })
      })
    )
  }
}
