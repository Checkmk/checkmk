/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostRef } from '@/monitoring/shared/api/types'

export type DiscoveredGraph = components['schemas']['ApiDiscoveredGraph']

export interface DiscoveredServiceGraphs {
  graphs: DiscoveredGraph[]
  /** Why a service has no graphs, in the backend's words. Null when it has some. */
  noDataMessage: string | null
}

export class ServiceGraphsApi {
  public async discover(host: HostRef, description: string): Promise<DiscoveredServiceGraphs> {
    const response = await unwrap(
      await client.POST('/domain-types/graph/actions/discover_template_graphs/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          hostname: host.name,
          service_description: description,
          site: host.site_id,
          graph_id: null
        }
      })
    )
    return { graphs: response.graphs, noDataMessage: response.no_data_message ?? null }
  }
}
