/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostRef } from '@/monitoring/shared/api/types'

export class ArchiveEventsApi {
  /** Archives the open Event Console events of the hosts, returning how many hosts it covered. */
  public async archiveHostEvents(hosts: HostRef[]): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/archive_events', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { hosts }
      })
    )
    return response.archived
  }
}
