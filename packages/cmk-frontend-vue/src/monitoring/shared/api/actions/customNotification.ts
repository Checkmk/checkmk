/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { serviceTargets } from '@/monitoring/shared/api/actions/targets'
import type { HostRef, ServiceRef } from '@/monitoring/shared/api/types'

export interface CustomNotificationOptions {
  comment: string
  /** Send regardless of restrictions such as the notification period. */
  forced: boolean
  /** Send to all contacts. */
  broadcast: boolean
}

export class CustomNotificationApi {
  public async notifyHosts(hosts: HostRef[], options: CustomNotificationOptions): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/custom_notification', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { hosts, ...options }
      })
    )
    return response.notified
  }

  public async notifyServices(
    services: ServiceRef[],
    options: CustomNotificationOptions
  ): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/services/actions/custom_notification', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          services: serviceTargets(services),
          ...options
        }
      })
    )
    return response.notified
  }
}
