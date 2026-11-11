/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { HostRef } from '@/monitoring/shared/api/types'

const HOST_KEY = 'host'
const SITE_KEY = 'site'

export const hostPanelFragment = {
  keys: [HOST_KEY, SITE_KEY] as readonly string[],

  encode(host: HostRef): Record<string, string> {
    return { [HOST_KEY]: host.name, [SITE_KEY]: host.site_id }
  },

  decode(params: Record<string, string>): HostRef | null {
    const name = params[HOST_KEY]
    const siteId = params[SITE_KEY]
    return name === undefined || name === '' || siteId === undefined || siteId === ''
      ? null
      : { site_id: siteId, name }
  }
}
