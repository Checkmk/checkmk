/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from '@/lib/rest-api-client/client'

import type { Suggestion } from '@/components/CmkSuggestions'

export const fetchTagetSuggestions = async (linkType: string): Promise<Suggestion[]> => {
  if (linkType === 'dashboards') {
    const dashboards = unwrap(await client.GET('/domain-types/dashboard_metadata/collections/all'))
    return dashboards.value.map(
      (dashboard) =>
        ({
          name: dashboard.id!,
          title: dashboard.extensions.name!
        }) as Suggestion
    )
  }

  if (linkType === 'views') {
    const views = unwrap(await client.GET('/domain-types/view/collections/all'))
    return views.value.map((view) => ({ name: view.id!, title: view.title! }) as Suggestion)
  }

  return []
}
