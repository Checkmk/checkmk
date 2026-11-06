/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { serviceTargets } from '@/monitoring/shared/api/actions/targets'
import type { HostRef, ServiceRef } from '@/monitoring/shared/api/types'

export class CommentApi {
  public async commentHosts(hosts: HostRef[], comment: string): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/add_comment', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { hosts, comment }
      })
    )
    return response.commented
  }

  public async commentServices(services: ServiceRef[], comment: string): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/services/actions/add_comment', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { services: serviceTargets(services), comment }
      })
    )
    return response.commented
  }
}
