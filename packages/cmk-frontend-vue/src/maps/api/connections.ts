/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The monitoring connections the daemon polls, and what only it can answer.
 *
 * Connections are configured in Checkmk's global settings, so the SPA only reads
 * them. The other calls here are the ones that need the daemon's own Livestatus
 * session: the flow topology, metric history and an object's extended detail.
 */
import { unwrapDaemonResponse } from 'cmk-ui-library/lib/daemon-client/client'

import type { MapsDaemonClient } from '@/maps/api/transport'
import type {
  ConnectionConfig,
  MetricHistoryResponse,
  ObjectDetails,
  TopologyNode
} from '@/maps/types/api'

/** How far a flow topology reaches, when the map's own view does not say. */
export interface TopologyScope {
  root?: string | null
  childLayers?: number | null
  parentLayers?: number | null
  topAffectedHosts?: number | null
  servicesPerHost?: number | null
}

export class ConnectionsApi {
  public constructor(private readonly client: MapsDaemonClient) {}

  public async list(): Promise<ConnectionConfig[]> {
    return unwrapDaemonResponse(await this.client.GET('/api/v1/connections'))
  }

  public async fetchTopology(
    connectionId: string,
    includeServices = false,
    scope: TopologyScope = {}
  ): Promise<TopologyNode[]> {
    return unwrapDaemonResponse(
      await this.client.GET('/api/v1/connections/{connection_id}/topology', {
        params: {
          path: { connection_id: connectionId },
          query: {
            ...(includeServices && { include_services: true }),
            ...(scope.root !== null && scope.root !== undefined && { root: scope.root }),
            ...(scope.childLayers !== null &&
              scope.childLayers !== undefined && { child_layers: scope.childLayers }),
            ...(scope.parentLayers !== null &&
              scope.parentLayers !== undefined && { parent_layers: scope.parentLayers }),
            ...(scope.topAffectedHosts !== null &&
              scope.topAffectedHosts !== undefined && {
                top_affected_hosts: scope.topAffectedHosts
              }),
            ...(scope.servicesPerHost !== null &&
              scope.servicesPerHost !== undefined && { services_per_host: scope.servicesPerHost })
          }
        }
      })
    )
  }

  public async fetchMetricHistory(
    connectionId: string,
    host: string,
    service: string | null,
    minutes: number
  ): Promise<MetricHistoryResponse> {
    return unwrapDaemonResponse(
      await this.client.GET('/api/v1/connections/{connection_id}/metric-history', {
        params: {
          path: { connection_id: connectionId },
          query: { host, minutes, ...(service && { service }) }
        }
      })
    )
  }

  public async fetchObjectDetails(
    connectionId: string,
    objectType: 'host' | 'service',
    host: string,
    service: string | null
  ): Promise<ObjectDetails | null> {
    return unwrapDaemonResponse(
      await this.client.GET('/api/v1/connections/{connection_id}/object-details', {
        params: {
          path: { connection_id: connectionId },
          query: { type: objectType, host, ...(service && { service }) }
        }
      })
    )
  }
}
