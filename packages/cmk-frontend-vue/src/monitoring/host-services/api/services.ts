/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { MonitoringApi, type MonitoringQueryParams } from '@/monitoring/shared/api/MonitoringApi'
import type {
  FilterNode,
  HostRef,
  HostServicesResponse,
  ServiceFilterNode,
  ServiceOptionalField,
  ServiceOverview,
  ServiceRef,
  ServicesRequestBody
} from '@/monitoring/shared/api/types'

export interface HostServicesQueryParams extends MonitoringQueryParams {
  // `FilterNode` spans every monitoring page's fields; the API only accepts the service-scoped
  // `ServiceFilterNode` schema, generated separately from the host one (e.g. `state`'s allowed
  // values differ between the two), hence the `unknown` bridge below rather than a direct cast.
  filter?: FilterNode | undefined
  fields?: ServiceOptionalField[] | undefined
}

export class HostServicesApi extends MonitoringApi {
  public async fetchServices(
    host: HostRef,
    params: HostServicesQueryParams = {},
    signal?: AbortSignal
  ): Promise<HostServicesResponse> {
    const body: ServicesRequestBody = {
      ...this.buildRequestBody(params),
      ...(params.filter && {
        filter: params.filter as unknown as ServiceFilterNode
      }),
      ...(params.fields !== undefined && { fields: params.fields })
    }
    return unwrap(
      await client.POST('/monitor/hosts/{hostname}/services', {
        params: {
          path: { hostname: host.name },
          query: { site_id: host.site_id },
          header: { 'Content-Type': 'application/json' }
        },
        body,
        ...(signal && { signal })
      })
    )
  }

  public async fetchServiceOverview(service: ServiceRef): Promise<ServiceOverview> {
    return unwrap(
      await client.GET('/monitor/hosts/{hostname}/service', {
        params: {
          path: { hostname: service.host.name },
          query: { site_id: service.host.site_id, service_name: service.description }
        }
      })
    )
  }
}
