/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from '@/lib/rest-api-client/client'

import type { HostsRequest, HostsResponse } from '../../shared/api/types'

export class HostApi {
  public async fetchHosts(params?: HostsRequest): Promise<HostsResponse> {
    return unwrap(
      await client.GET('/monitor/hosts', {
        params: params !== undefined ? { query: params } : {}
      })
    )
  }
}
