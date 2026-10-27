/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { hostNameQuery, serviceQuery } from '@/monitoring/shared/api/actions/query'
import type { ServiceRef } from '@/monitoring/shared/api/types'

// Like the legacy command, a comment survives a restart of the core.
const PERSISTENT = true

export class CommentApi {
  public async commentHosts(hostNames: string[], comment: string): Promise<void> {
    unwrap(
      await client.POST('/domain-types/comment/collections/host', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          comment_type: 'host_by_query',
          query: hostNameQuery(hostNames),
          comment,
          persistent: PERSISTENT
        }
      })
    )
  }

  public async commentServices(services: ServiceRef[], comment: string): Promise<void> {
    unwrap(
      await client.POST('/domain-types/comment/collections/service', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          comment_type: 'service_by_query',
          query: serviceQuery(services),
          comment,
          persistent: PERSISTENT
        }
      })
    )
  }
}
