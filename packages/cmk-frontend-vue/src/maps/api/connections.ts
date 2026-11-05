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
 * session: metric history and an object's extended detail.
 */
import type { MapsDaemonClient } from '@/maps/api/transport'
import type { ConnectionConfig, MetricHistoryResponse, ObjectDetails } from '@/maps/types/api'

export class ConnectionsApi {
  public constructor(private readonly client: MapsDaemonClient) {}

  public async list(): Promise<ConnectionConfig[]> {
    return this.client.GET('/api/v1/connections')
  }

  public async fetchMetricHistory(
    connectionId: string,
    host: string,
    service: string | null,
    minutes: number
  ): Promise<MetricHistoryResponse> {
    return this.client.GET('/api/v1/connections/{connection_id}/metric-history', {
      params: {
        path: { connection_id: connectionId },
        query: { host, minutes, ...(service && { service }) }
      }
    })
  }

  public async fetchObjectDetails(
    connectionId: string,
    objectType: 'host' | 'service',
    host: string,
    service: string | null
  ): Promise<ObjectDetails | null> {
    return this.client.GET('/api/v1/connections/{connection_id}/object-details', {
      params: {
        path: { connection_id: connectionId },
        query: { type: objectType, host, ...(service && { service }) }
      }
    })
  }
}
