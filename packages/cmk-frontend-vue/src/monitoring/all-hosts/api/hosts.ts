/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState } from '@tanstack/vue-table'

import client, { unwrap } from '@/lib/rest-api-client/client'

import type { HostsRequest, HostsResponse } from '../../shared/api/types'

export interface HostQueryParams {
  limit?: number
  sort?: SortingState
}

export class HostApi {
  public async fetchHosts(params: HostQueryParams = {}): Promise<HostsResponse> {
    const sort = (params.sort ?? []).map((s) => `${s.id}:${s.desc ? 'desc' : 'asc'}`)
    // The schema types limit as string and sort as string (not string[]); openapi-fetch's
    // defaultQuerySerializer handles string[] as repeated params at runtime, so the cast
    // is only needed to bridge the incorrectly-generated schema types.
    return unwrap(
      await client.GET('/monitor/hosts', {
        params: {
          query: {
            ...(params.limit !== undefined && { limit: String(params.limit) }),
            ...(sort.length > 0 && { sort })
          } as unknown as NonNullable<HostsRequest>
        }
      })
    )
  }
}
