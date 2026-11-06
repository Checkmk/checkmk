/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { serviceTargets } from '@/monitoring/shared/api/actions/targets'
import type { HostRef, ServiceRef } from '@/monitoring/shared/api/types'

export interface AcknowledgeOptions {
  comment: string
  sticky: boolean
  persistent: boolean
  notify: boolean
  expireOn?: string | undefined
}

export class AcknowledgeApi {
  public async acknowledgeHosts(hosts: HostRef[], options: AcknowledgeOptions): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/acknowledge', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { hosts, ...this.commonFields(options) }
      })
    )
    return response.acknowledged
  }

  public async acknowledgeServices(
    services: ServiceRef[],
    options: AcknowledgeOptions
  ): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/services/actions/acknowledge', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { services: serviceTargets(services), ...this.commonFields(options) }
      })
    )
    return response.acknowledged
  }

  public async removeHostAcknowledgements(hosts: HostRef[]): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/remove_acknowledgements', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { hosts }
      })
    )
    return response.removed
  }

  public async removeServiceAcknowledgements(services: ServiceRef[]): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/services/actions/remove_acknowledgements', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { services: serviceTargets(services) }
      })
    )
    return response.removed
  }

  private commonFields(options: AcknowledgeOptions) {
    return {
      comment: options.comment,
      sticky: options.sticky,
      persistent: options.persistent,
      notify: options.notify,
      ...(options.expireOn && { expire_on: options.expireOn })
    }
  }
}
