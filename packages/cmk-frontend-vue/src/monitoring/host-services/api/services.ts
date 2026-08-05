/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostServicesResponse } from '@/monitoring/shared/api/types'

const DEFAULT_SERVICE_LIMIT = 1000

export class HostServicesApi {
  public async fetchServices(
    host: string,
    site: string,
    signal?: AbortSignal
  ): Promise<HostServicesResponse> {
    return unwrap(
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
  }
}
