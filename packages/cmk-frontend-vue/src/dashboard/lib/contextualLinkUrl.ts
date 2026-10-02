/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FilterResult, ResolvedLink, VisualContext } from '@/dashboard/types/widget'

const PAGE_BY_LOCATION_TYPE: Record<ResolvedLink['location']['type'], [string, string]> = {
  views: ['view.py', 'view_name'],
  dashboards: ['dashboard.py', 'name']
}

/** The URL of a resolved link for one element, with the effective context underneath. */
export function contextualLinkUrl(
  link: ResolvedLink,
  properties: Record<string, FilterResult>,
  effectiveContext: VisualContext
): string {
  const [page, nameVariable] = PAGE_BY_LOCATION_TYPE[link.location.type]
  const filters: VisualContext = {
    ...(link.include_context ? effectiveContext : {}),
    ...Object.fromEntries(
      Object.entries(properties).flatMap(([filterId, result]) =>
        result.status === 'encoded' ? [[filterId, result.variables]] : []
      )
    )
  }
  const params = new URLSearchParams({ [nameVariable]: link.location.name })
  // Without an owner, the target page resolves the name for each viewer.
  if (link.location.owner !== null) {
    params.set('owner', link.location.owner)
  }
  for (const variables of Object.values(filters)) {
    for (const [variable, value] of Object.entries(variables)) {
      params.set(variable, value)
    }
  }
  params.set('filled_in', 'filter')
  params.set('_show_filter_form', link.show_filter_form ? '1' : '0')
  return `${page}?${params.toString()}`
}
