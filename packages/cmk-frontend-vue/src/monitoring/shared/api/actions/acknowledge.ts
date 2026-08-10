/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { hostNameQuery, serviceDescriptionQuery } from '@/monitoring/shared/api/actions/query'

export type AcknowledgeHostQueryProblem = components['schemas']['AcknowledgeHostQueryProblem']

export type AcknowledgeServiceQueryProblem = components['schemas']['AcknowledgeServiceQueryProblem']

export interface AcknowledgeOptions {
  comment: string
  sticky: boolean
  persistent: boolean
  notify: boolean
  expireOn?: string | undefined
}

export class AcknowledgeApi {
  public async acknowledgeHosts(hostNames: string[], options: AcknowledgeOptions): Promise<void> {
    const body: AcknowledgeHostQueryProblem = {
      acknowledge_type: 'host_by_query',
      query: hostNameQuery(hostNames),
      ...this.commonFields(options)
    }
    unwrap(
      await client.POST('/domain-types/acknowledge/collections/host', {
        params: { header: { 'Content-Type': 'application/json' } },
        body
      })
    )
  }

  public async acknowledgeServices(
    hostName: string,
    serviceDescriptions: string[],
    options: AcknowledgeOptions
  ): Promise<void> {
    const body: AcknowledgeServiceQueryProblem = {
      acknowledge_type: 'service_by_query',
      query: serviceDescriptionQuery(hostName, serviceDescriptions),
      ...this.commonFields(options)
    }
    unwrap(
      await client.POST('/domain-types/acknowledge/collections/service', {
        params: { header: { 'Content-Type': 'application/json' } },
        body
      })
    )
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
