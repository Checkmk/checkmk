/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from '@/lib/rest-api-client/client'

import type { Suggestion } from '@/components/CmkSuggestions'

export const fetchDashboards = async (): Promise<Suggestion[]> => {
  const dashboards = unwrap(await client.GET('/domain-types/dashboard_metadata/collections/all'))
  return dashboards.value.map(
    (dashboard) =>
      ({
        name: dashboard.extensions.name,
        title: dashboard.extensions.display.title
      }) as Suggestion
  )
}
