/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkMenuLink, CmkMenuLinkItem } from 'cmk-ui-library/components/CmkMenu'

import { contextualLinkEntries } from '@/dashboard/lib/contextualLinkUrl'
import type { GraphLinks, GraphService, VisualContext } from '@/dashboard/types/widget'
import type { Metric, RequestedTimeRange } from '@/graphing'
import type { TimeRangeVariables } from '@/graphing/GlobalTimePicker/timeRangeUrl'

export type GraphLinkOffer =
  | { type: 'none' }
  | { type: 'link'; link: CmkMenuLink }
  | { type: 'menu'; items: CmkMenuLinkItem[] }

/** What every link of a graph carries besides the filters of its service. */
export interface GraphLinkSurroundings {
  context: VisualContext
  drilledFrom: string | null
  timeRange: RequestedTimeRange
}

type ServiceLinks = GraphLinks['services'][number]

// GRAPH_LINK_SERVICE_LIMIT of compute-graph-links; the lines of further services offer no links.
const SERVICE_LIMIT = 200

// The endpoint answers the services as they were asked, so this key joins a line to its links.
function serviceKey(service: GraphService): string {
  return JSON.stringify([service.site_id, service.host_name, service.service_description])
}

/** The services the lines of a graph are drawn for, each once, in the order of their lines. */
export function drawnServices(metrics: Metric[]): GraphService[] {
  const services = new Map<string, GraphService>()
  for (const { metadata } of metrics) {
    if (services.size === SERVICE_LIMIT) {
      break
    }
    if (metadata.origin && !services.has(serviceKey(metadata.origin))) {
      services.set(serviceKey(metadata.origin), metadata.origin)
    }
  }
  return [...services.values()]
}

// A graph's window is in seconds; links carry instants in epoch milliseconds.
function windowVariables({ start, end }: RequestedTimeRange): TimeRangeVariables {
  return { from: String(Math.round(start * 1000)), to: String(Math.round(end * 1000)) }
}

function linksOf(
  resolved: GraphLinks,
  service: ServiceLinks,
  { context, drilledFrom, timeRange }: GraphLinkSurroundings
): CmkMenuLink[] {
  return contextualLinkEntries(
    resolved.links,
    service.link_properties,
    context,
    windowVariables(timeRange),
    drilledFrom
  ).map(({ title, href }) => ({ title, url: href }))
}

function menuOrNone(items: CmkMenuLinkItem[]): GraphLinkOffer {
  return items.length === 0 ? { type: 'none' } : { type: 'menu', items }
}

function serviceLinkOffer(links: CmkMenuLink[]): GraphLinkOffer {
  const [first] = links
  if (first !== undefined && links.length === 1) {
    return { type: 'link', link: first }
  }
  return menuOrNone(
    links.map((link): CmkMenuLinkItem => ({ label: [{ text: link.title }], links: [link] }))
  )
}

function lineMenuOffer(
  resolved: GraphLinks,
  metrics: Metric[],
  surroundings: GraphLinkSurroundings
): GraphLinkOffer {
  const servicesByKey = new Map(resolved.services.map((service) => [serviceKey(service), service]))
  return menuOrNone(
    metrics.flatMap(({ metadata }): CmkMenuLinkItem[] => {
      const service = metadata.origin && servicesByKey.get(serviceKey(metadata.origin))
      if (!service) {
        return []
      }
      const [first, ...rest] = linksOf(resolved, service, surroundings)
      if (first === undefined) {
        return []
      }
      return [
        {
          color: metadata.color,
          label: [
            { text: service.host_name, truncateOrder: 1 },
            { text: service.service_description, truncateOrder: 2 },
            { text: metadata.title, bold: true, line: 2, truncateOrder: 3 }
          ],
          links: [first, ...rest]
        }
      ]
    })
  )
}

/**
 * A graph drawing one service offers that service's links. A graph drawing several offers its
 * lines instead, each with the links of the service it is drawn for.
 */
export function graphLinkOffer(
  resolved: GraphLinks,
  metrics: Metric[],
  surroundings: GraphLinkSurroundings
): GraphLinkOffer {
  const [only] = resolved.services
  if (only !== undefined && resolved.services.length === 1) {
    return serviceLinkOffer(linksOf(resolved, only, surroundings))
  }
  return lineMenuOffer(resolved, metrics, surroundings)
}
