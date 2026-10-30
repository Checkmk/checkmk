/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostRef, ServiceRef } from '@/monitoring/shared/api/types'

export interface RescheduleResult {
  /** How many checks were rescheduled. */
  rescheduled: number
  /**
   * The time at which the checks were rescheduled. A check has run again once it last ran at or
   * after this time.
   */
  scheduledAt: number
  /** How long to wait for a rescheduled check to run, in seconds. */
  waitTimeoutSeconds: number
}

function rescheduleResult(response: {
  rescheduled: number
  scheduled_at: number
  wait_timeout: number
}): RescheduleResult {
  return {
    rescheduled: response.rescheduled,
    scheduledAt: response.scheduled_at,
    waitTimeoutSeconds: response.wait_timeout
  }
}

export class RescheduleApi {
  public async rescheduleHosts(hosts: HostRef[], spreadMinutes: number): Promise<RescheduleResult> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/reschedule', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { hosts, spread_minutes: spreadMinutes }
      })
    )
    return rescheduleResult(response)
  }

  public async rescheduleServices(
    services: ServiceRef[],
    spreadMinutes: number
  ): Promise<RescheduleResult> {
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
    return rescheduleResult(response)
  }
}
