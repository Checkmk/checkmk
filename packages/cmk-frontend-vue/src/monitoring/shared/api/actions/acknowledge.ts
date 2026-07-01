/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import client, { unwrap } from '@/lib/rest-api-client/client'

export type AcknowledgeHostQueryProblem = components['schemas']['AcknowledgeHostQueryProblem']

export interface AcknowledgeHostOptions {
  comment: string
  sticky: boolean
  persistent: boolean
  notify: boolean
  expireOn?: string | undefined
}

export class AcknowledgeApi {
  public async acknowledgeHosts(
    hostNames: string[],
    options: AcknowledgeHostOptions
  ): Promise<void> {
    const body: AcknowledgeHostQueryProblem = {
      acknowledge_type: 'host_by_query',
      query: {
        op: 'or',
        expr: hostNames.map((hostName) => ({ op: '=', left: 'name', right: hostName }))
      },
      comment: options.comment,
      sticky: options.sticky,
      persistent: options.persistent,
      notify: options.notify,
      ...(options.expireOn && { expire_on: options.expireOn })
    }
    unwrap(
      await client.POST('/domain-types/acknowledge/collections/host', {
        params: { header: { 'Content-Type': 'application/json' } },
        body
      })
    )
  }
}
