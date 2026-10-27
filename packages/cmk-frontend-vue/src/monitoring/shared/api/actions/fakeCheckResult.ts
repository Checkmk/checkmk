/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostRef, ServiceRef } from '@/monitoring/shared/api/types'

type HostCheckState = components['schemas']['FakeCheckResultRequestBody']['state']
type ServiceCheckState = components['schemas']['FakeCheckResultServicesRequestBody']['state']

export interface FakeCheckResultOptions {
  state: number
  pluginOutput: string
  metrics: string
}

export class FakeCheckResultApi {
  public async fakeHosts(hosts: HostRef[], options: FakeCheckResultOptions): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/fake_check_result', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          hosts,
          // The form offers a host only the states of a host.
          state: options.state as HostCheckState,
          plugin_output: options.pluginOutput,
          metrics: options.metrics
        }
      })
    )
    return response.faked
  }

  public async fakeServices(
    services: ServiceRef[],
    options: FakeCheckResultOptions
  ): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/services/actions/fake_check_result', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          services: services.map((service) => ({
            site_id: service.host.site_id,
            host_name: service.host.name,
            name: service.description
          })),
          state: options.state as ServiceCheckState,
          plugin_output: options.pluginOutput,
          metrics: options.metrics
        }
      })
    )
    return response.faked
  }
}
