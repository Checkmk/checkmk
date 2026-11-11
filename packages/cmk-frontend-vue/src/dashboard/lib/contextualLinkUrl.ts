/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type {
  FilterResult,
  LinkProperties,
  ResolvedLink,
  StatsLinkPart,
  VisualContext
} from '@/dashboard/types/widget'
import {
  type TimeRangeVariables,
  setTimeRangeVariables
} from '@/graphing/GlobalTimePicker/timeRangeUrl'
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
  timeRange: TimeRangeVariables | null,
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
  for (const variables of Object.values(filters)) {
    for (const [variable, value] of Object.entries(variables)) {
      params.set(variable, value)
    }
  }
  if (link.include_time_range && timeRange !== null) {
    setTimeRangeVariables(params, timeRange)
  }
  params.set('filled_in', 'filter')
  params.set('_show_filter_form', link.show_filter_form ? '1' : '0')
  const dropped = Object.entries(properties).flatMap(([filterId, result]) => {
    // A key the clicked element lacks drops alone, while the filter carries the others.
    if (result.status === 'encoded') {
      return (result.missing_keys ?? []).map((key) => `${filterId}:no_such_key:${key}`)
    }
    // A filter the context carries in place of the clicked element's value still travels.
    if (filterId in filters) {
      return []
    }
    // A deferred filter the click could not value.
    if (result.status === 'deferred') {
      return [`${filterId}:no_value`]
    }
    const missingKeys = result.missing_keys ?? []
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

/** How many links of an element lead anywhere, as `contextualLinkEntries` lists them. */
export function contextualLinkCount(links: ResolvedLink[], linkProperties: LinkProperties): number {
  return links.filter((_link, index) => linkProperties.links[index] !== undefined).length
}

/**
 * Each link of an element with its URL, in the order the widget offers them. A link with a
 * deferred filter leads to `deferredHref`, which values that filter before it opens the link.
 */
export function contextualLinkEntries(
  links: ResolvedLink[],
  linkProperties: LinkProperties,
  effectiveContext: VisualContext,
  timeRange: TimeRangeVariables | null,
  drilledFrom: string | null,
  deferredHref?: ((linkIndex: number) => string) | undefined
): ContextualLinkEntry[] {
  return links.flatMap((link, index) => {
    const properties = linkProperties.links[index]
    if (properties === undefined) {
      return []
    }
    const deferred = Object.values(properties).some((result) => result.status === 'deferred')
    return [
      {
        title: link.title,
        href:
          deferred && deferredHref
            ? deferredHref(index)
            : contextualLinkUrl(link, properties, effectiveContext, timeRange, drilledFrom)
      }
    ]
  })
}

/**
 * The page that opens a statistics widget's link from its part or its total, after it valued
 * the link's deferred filters from the objects the click stands for.
 */
export function statsLinkUrl(
  dashboardKey: DashboardKey,
  widgetId: string,
  part: StatsLinkPart,
  linkIndex: number,
  effectiveContext: VisualContext,
  timeRange: TimeRangeVariables | null,
  drilledFrom: string | null
): string {
  const params = new URLSearchParams({
    dashboard_name: dashboardKey.name,
    dashboard_owner: dashboardKey.owner,
    widget_id: widgetId,
    part,
    link_index: String(linkIndex),
    context: JSON.stringify(effectiveContext)
  })
  if (timeRange !== null) {
    setTimeRangeVariables(params, timeRange)
  }
  if (drilledFrom) {
    params.set(DRILLED_FROM_PARAM, drilledFrom)
  }
  return `dashboard_stats_link.py?${params.toString()}`
}

/** The URL of the first contextual link, or null if the widget links nowhere. */
export function firstContextualLinkUrl(
  links: ResolvedLink[],
  linkProperties: LinkProperties,
  effectiveContext: VisualContext,
  timeRange: TimeRangeVariables | null,
  drilledFrom: string | null
): string | null {
  const link = links[0]
  const properties = linkProperties.links[0]
  if (link === undefined || properties === undefined) {
    return null
  }
  return contextualLinkUrl(link, properties, effectiveContext, timeRange, drilledFrom)
}
