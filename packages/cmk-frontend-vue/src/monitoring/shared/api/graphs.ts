/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { type DiscoveredGraph, notBuildableReason } from '@/graphing/api/discoveredGraph'
import type { HostRef } from '@/monitoring/shared/api/types'

export interface DiscoveredGraphs {
  graphs: DiscoveredGraph[]
  /** Why there are no graphs, in the backend's words. Null when there are some. */
  noDataMessage: string | null
  /** Why the graphs cannot be built, in the backend's words. Null when they can. */
  errorMessage: string | null
}

// The service name the graphing backend reads as the host itself, as the legacy views pass it.
const HOST_PSEUDO_SERVICE = '_HOST_'

export class GraphsApi {
  /** Discovers the graphs of a service of the host, or of the host itself without a service. */
  public async discover(host: HostRef, service?: string): Promise<DiscoveredGraphs> {
    try {
      const response = await unwrap(
        await client.POST('/domain-types/graph/actions/discover_template_graphs/invoke', {
          params: { header: { 'Content-Type': 'application/json' } },
          body: {
            hostname: host.name,
            service_description: service ?? HOST_PSEUDO_SERVICE,
            site: host.site_id,
            graph_id: null
          }
        })
      )
      return {
        graphs: response.graphs,
        noDataMessage: response.no_data_message ?? null,
        errorMessage: null
      }
    } catch (error) {
      const reason = notBuildableReason(error)
      if (reason === null) {
        throw error
      }
      return { graphs: [], noDataMessage: null, errorMessage: reason }
    }
  }
}
