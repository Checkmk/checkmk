/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState } from '@tanstack/vue-table'

import client, { unwrap } from '@/lib/rest-api-client/client'

import type { RequestedLimit } from '@/monitoring/shared/services/MonitoringService'

import type {
  FilterNode,
  HostOverview,
  HostRef,
  HostsRequestBody,
  HostsResponse
} from '../../shared/api/types'
import { DEFAULT_BATCH_SIZE } from '../../shared/constants'

export interface HostQueryParams {
  limit?: RequestedLimit
  sort?: SortingState
  searchQuery?: string
  filter?: FilterNode | undefined
}

export class HostApi {
  public async fetchHosts(
    params: HostQueryParams = {},
    signal?: AbortSignal
  ): Promise<HostsResponse> {
    const sort = (params.sort ?? []).map((s) => `${s.id}:${s.desc ? 'desc' : 'asc'}`)
    const searchQuery = params.searchQuery?.trim()
    const body: HostsRequestBody = {
      limit: params.limit === undefined ? DEFAULT_BATCH_SIZE : params.limit,
      ...(sort.length > 0 && { sort }),
      ...(searchQuery && { q: searchQuery }),
      ...(params.filter && { filter: params.filter })
    }
    return unwrap(
      await client.POST('/monitor/hosts', {
        params: { header: { 'Content-Type': 'application/json' } },
        body,
        ...(signal && { signal })
      })
    )
  }

  public async fetchHostOverview(host: HostRef): Promise<HostOverview> {
    return unwrap(
      await client.GET('/monitor/hosts/{hostname}', {
        params: {
          path: { hostname: host.name },
          query: { site_id: host.site_id }
        }
      })
    )
  }
}
