/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

export interface DashboardTarget {
  name: string
  title: string
}

/** The dashboards a link may open, one per name. */
export const fetchDashboardTargets = async (): Promise<DashboardTarget[]> => {
  const dashboards = unwrap(await client.GET('/domain-types/dashboard_metadata/collections/all'))
  return dashboards.value.map((dashboard) => ({
    name: dashboard.extensions.name,
    title: dashboard.extensions.display.title
  }))
}

/** The dashboards as dropdown options, sorted by title. */
export function dashboardOptions(dashboards: DashboardTarget[]): Suggestion[] {
  return dashboards
    .map((dashboard) => ({
      name: dashboard.name,
      title: untranslated(`${dashboard.title} (${dashboard.name})`)
    }))
    .sort((a, b) => a.title.localeCompare(b.title))
}
