/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from '@/lib/rest-api-client/client'

import type { ActionMenuItem, HostRef } from '../../shared/api/types'

export class HostActionMenuApi {
  public async fetchActionMenu(host: HostRef): Promise<ActionMenuItem[]> {
    const response = unwrap(
      await client.GET('/monitor/hosts/{hostname}/action_menu', {
        params: { path: { hostname: host.name }, query: { site_id: host.site_id } }
      })
    )
    return response.items
  }
}
