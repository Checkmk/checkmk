/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  FilterResult,
  LinkProperties,
  ResolvedLink,
  VisualContext
} from '@/dashboard/types/widget'
import { DRILLED_FROM_PARAM } from '@/page-header/drillUp'

const PAGE_BY_LOCATION_TYPE: Record<ResolvedLink['location']['type'], [string, string]> = {
  views: ['view.py', 'view_name'],
  dashboards: ['dashboard.py', 'name']
}

/** The URL of a resolved link for one element, with the effective context underneath. */
export function contextualLinkUrl(
  link: ResolvedLink,
  properties: Record<string, FilterResult>,
  effectiveContext: VisualContext,
  drilledFrom: string | null
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
  const dropped = Object.entries(properties).flatMap(([filterId, result]) => {
    const missingKeys = result.missing_keys ?? []
    // A key the clicked element lacks drops alone, while the filter carries the others.
    if (result.status === 'encoded') {
      return missingKeys.map((key) => `${filterId}:no_such_key:${key}`)
    }
    // A filter the context carries in place of the clicked element's value still travels.
    if (filterId in filters) {
      return []
    }
    return missingKeys.length > 0
      ? missingKeys.map((key) => `${filterId}:${result.reason}:${key}`)
      : [`${filterId}:${result.reason}`]
  })
  if (dropped.length > 0) {
    params.set('_dropped_filters', dropped.join(','))
  }
  if (drilledFrom) {
    params.set(DRILLED_FROM_PARAM, drilledFrom)
  }
  return `${page}?${params.toString()}`
}

export interface ContextualLinkEntry {
  title: string
  href: string
}

/** Each link of an element with its URL, in the order the widget offers them. */
export function contextualLinkEntries(
  links: ResolvedLink[],
  linkProperties: LinkProperties,
  effectiveContext: VisualContext,
  drilledFrom: string | null
): ContextualLinkEntry[] {
  return links.flatMap((link, index) => {
    const properties = linkProperties.links[index]
    return properties === undefined
      ? []
      : [
          {
            title: link.title,
            href: contextualLinkUrl(link, properties, effectiveContext, drilledFrom)
          }
        ]
  })
}

/** The URL of the first contextual link, or null if the widget links nowhere. */
export function firstContextualLinkUrl(
  links: ResolvedLink[],
  linkProperties: LinkProperties,
  effectiveContext: VisualContext,
  drilledFrom: string | null
): string | null {
  const link = links[0]
  const properties = linkProperties.links[0]
  if (link === undefined || properties === undefined) {
    return null
  }
  return contextualLinkUrl(link, properties, effectiveContext, drilledFrom)
}
