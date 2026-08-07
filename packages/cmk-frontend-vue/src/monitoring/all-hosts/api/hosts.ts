/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { MonitoringApi, type MonitoringQueryParams } from '@/monitoring/shared/api/MonitoringApi'

import type {
  FilterNode,
  HostOptionalField,
  HostOverview,
  HostRef,
  HostsRequestBody,
  HostsResponse
} from '../../shared/api/types'

export interface HostQueryParams extends MonitoringQueryParams {
  // `FilterNode` spans every monitoring page's fields, including service-only ones like
  // `summary`; the API only accepts the host's own generated schema, and this page only ever
  // puts host fields into it, hence the cast below rather than a direct assignment.
  filter?: FilterNode | undefined
  fields?: HostOptionalField[]
}

export class HostApi extends MonitoringApi {
  public async fetchHosts(
    params: HostQueryParams = {},
    signal?: AbortSignal
  ): Promise<HostsResponse> {
    const body: HostsRequestBody = {
      ...this.buildRequestBody(params),
      ...(params.filter && { filter: params.filter as NonNullable<HostsRequestBody['filter']> }),
      ...(params.fields !== undefined && { fields: params.fields })
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
