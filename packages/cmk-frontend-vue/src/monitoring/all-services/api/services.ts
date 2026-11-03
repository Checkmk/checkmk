/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostServicesQueryParams } from '@/monitoring/host-services/api/services'
import { MonitoringApi } from '@/monitoring/shared/api/MonitoringApi'
import type {
  AllServicesRequestBody,
  ServiceFilterNode,
  ServicesResponse
} from '@/monitoring/shared/api/types'

export class AllServicesApi extends MonitoringApi {
  public async fetchServices(
    params: HostServicesQueryParams = {},
    signal?: AbortSignal
  ): Promise<ServicesResponse> {
    const filter = this.resolveFilter(params.filter)
    const body: AllServicesRequestBody = {
      ...this.buildRequestBody(params),
      ...(filter && {
        filter: filter as unknown as ServiceFilterNode
      }),
      ...(params.fields !== undefined && { fields: params.fields })
    }
    return unwrap(
      await client.POST('/monitor/services', {
        params: { header: { 'Content-Type': 'application/json' } },
        body,
        ...(signal && { signal })
      })
    )
  }
}
