/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState } from '@tanstack/vue-table'

import client, { unwrap } from '@/lib/rest-api-client/client'

import type { HostsRequestBody, HostsResponse } from '../../shared/api/types'
import { DEFAULT_BATCH_SIZE } from '../../shared/constants'

export interface HostQueryParams {
  limit?: number
  sort?: SortingState
  searchQuery?: string
}

export class HostApi {
  public async fetchHosts(params: HostQueryParams = {}): Promise<HostsResponse> {
    const sort = (params.sort ?? []).map((s) => `${s.id}:${s.desc ? 'desc' : 'asc'}`)
    // Drop an empty or whitespace-only search query so an empty search matches a request without
    // the `q` param.
    const searchQuery = params.searchQuery?.trim()
    const body: HostsRequestBody = {
      limit: params.limit ?? DEFAULT_BATCH_SIZE,
      ...(sort.length > 0 && { sort }),
      ...(searchQuery && { q: searchQuery })
    }
    return unwrap(
      await client.POST('/monitor/hosts', {
        params: { header: { 'Content-Type': 'application/json' } },
        body
      })
    )
  }
}
