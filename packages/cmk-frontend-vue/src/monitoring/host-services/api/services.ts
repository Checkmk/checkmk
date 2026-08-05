/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { ServiceState } from '@/monitoring/shared/api/types'

type ApiServiceEntry = components['schemas']['HostServiceEntry']

const DEFAULT_SERVICE_LIMIT = 1000

export interface ServiceEntry {
  name: string
  state: ServiceState
  summary: string
  last_check: string
  last_state_change: string
}

export class HostServicesApi {
  public async fetchServices(
    host: string,
    site: string,
    signal?: AbortSignal
  ): Promise<ServiceEntry[]> {
    const response = unwrap(
      await client.POST('/monitor/hosts/{hostname}/services', {
        params: {
          path: { hostname: host },
          query: { site_id: site },
          header: { 'Content-Type': 'application/json' }
        },
        body: { limit: DEFAULT_SERVICE_LIMIT },
        ...(signal && { signal })
      })
    )
    return response.services.map((entry) => this.toEntry(entry))
  }

  private toEntry(entry: ApiServiceEntry): ServiceEntry {
    return {
      name: entry.name,
      state: entry.state,
      summary: entry.summary,
      last_check: entry.last_check,
      last_state_change: entry.last_state_change
    }
  }
}
