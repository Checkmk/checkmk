/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import type { MaybeRestApiError } from 'cmk-ui-library/lib/types'

import type { HostRef } from '@/monitoring/shared/api/types'

export type DiscoveredGraph = components['schemas']['ApiDiscoveredGraph']

export interface DiscoveredGraphs {
  graphs: DiscoveredGraph[]
  /** Why there are no graphs, in the backend's words. Null when there are some. */
  noDataMessage: string | null
  /** Why the graphs cannot be built, in the backend's words. Null when they can. */
  errorMessage: string | null
}

/** Dresses a discovered graph as the graph the renderer takes, at the size and interaction given. */
export function toTimeSeriesGraph(
  graph: DiscoveredGraph,
  size: CmkTimeSeriesGraph['size'],
  interaction: CmkTimeSeriesGraph['interaction']
): CmkTimeSeriesGraph {
  return {
    size,
    options: {
      header: { title: graph.title, show_graph_time: true },
      name: graph.name,
      x_axis: null,
      y_axis: graph.y_axis,
      font_size_pt: 8
    },
    interaction,
    internal: graph.internal,
    add_to: null,
    time_range: null
  }
}

const NOT_BUILDABLE_STATUS = 422
const NOT_BUILDABLE_TITLE = 'Graph cannot be built'

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
      const reason = GraphsApi.persistentFailureReason(error)
      if (reason === null) {
        throw error
      }
      return { graphs: [], noDataMessage: null, errorMessage: reason }
    }
  }

  private static persistentFailureReason(error: unknown): string | null {
    if (!(error instanceof CmkApiError) || error.statusCode !== NOT_BUILDABLE_STATUS) {
      return null
    }
    const body = error.body as MaybeRestApiError | undefined
    if (body?.title !== NOT_BUILDABLE_TITLE) {
      return null
    }
    return body.detail ?? null
  }
}
