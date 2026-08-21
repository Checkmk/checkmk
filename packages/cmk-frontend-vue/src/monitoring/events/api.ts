/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostRef } from '@/monitoring/shared/api/types'

export type EventsResponse = components['schemas']['EventsResponse']

export type EventEntry = components['schemas']['EventEntry']

/**
 * The recent events behind a slide-in's History tab.
 *
 * One endpoint serves both slide-ins: without `serviceName` it returns the host's own
 * events alongside those of all its services (the host slide-in), with it the events of
 * that one service (the service slide-in, CMK-38115). The time window and the row limit
 * stay the endpoint's defaults; the tab reads what was applied back off `meta` rather
 * than dictating it.
 */
export async function fetchEvents(host: HostRef, serviceName?: string): Promise<EventsResponse> {
  return unwrap(
    await client.GET('/monitor/hosts/{hostname}/events', {
      params: {
        path: { hostname: host.name },
        query: {
          site_id: host.site_id,
          ...(serviceName !== undefined && { service_name: serviceName })
        }
      }
    })
  )
}
