/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostRef, ServiceActionMenuItem } from './types'

export interface ServiceActionMenuOptions {
  /** Also list the links into Setup the user may follow, which the page offers nowhere else. */
  includeSetupLinks?: boolean
}

export class ServiceActionMenuApi {
  public async fetchActionMenu(
    host: HostRef,
    service: string,
    options: ServiceActionMenuOptions = {}
  ): Promise<ServiceActionMenuItem[]> {
    const response = unwrap(
      await client.GET('/monitor/hosts/{hostname}/service/action_menu', {
        params: {
          path: { hostname: host.name },
          query: {
            site_id: host.site_id,
            service_name: service,
            ...(options.includeSetupLinks === true ? { include_setup_links: 'true' } : {})
          }
        }
      })
    )
    return response.items
  }
}
