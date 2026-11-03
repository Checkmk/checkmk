/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostRef, ServiceRef } from '@/monitoring/shared/api/types'

export class RescheduleApi {
  public async rescheduleHosts(hosts: HostRef[], spreadMinutes: number): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/reschedule', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { hosts, spread_minutes: spreadMinutes }
      })
    )
    return response.rescheduled
  }

  public async rescheduleServices(services: ServiceRef[], spreadMinutes: number): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/services/actions/reschedule', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          services: services.map((service) => ({
            site_id: service.host.site_id,
            host_name: service.host.name,
            name: service.description
          })),
          spread_minutes: spreadMinutes
        }
      })
    )
    return response.rescheduled
  }
}
