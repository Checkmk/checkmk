/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

export interface DashboardTarget {
  name: string
  // As in a link location: '' for the built-in copy.
  owner: string
  title: string
}

export const fetchDashboardTargets = async (): Promise<DashboardTarget[]> => {
  const dashboards = unwrap(await client.GET('/domain-types/dashboard_metadata/collections/all'))
  return dashboards.value.map((dashboard) => ({
    name: dashboard.extensions.name,
    owner: dashboard.extensions.owner ?? '',
    title: dashboard.extensions.display.title
  }))
}
