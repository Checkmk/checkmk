/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How a flow map names the nodes it draws.
 *
 * The nodes come from a live topology, not from a saved map, so they have no
 * ids of their own — they are named after what they stand for. A host is named
 * after itself, everything below or beside it is named after the host it
 * belongs to. The names have to survive a topology push, because they are what
 * a remembered position, a selection and an open slide-in are keyed on.
 *
 * A service description may itself contain the separator, so the host is the
 * part before the *first* one and the service is everything after it.
 */

const SEPARATOR = '::'
const SITE_PREFIX = `__site__${SEPARATOR}`
const MORE_SUFFIX = `${SEPARATOR}__more__`

/** The kinds of node a flow map draws. */
export type FlowNodeKind = 'host' | 'service' | 'more' | 'site'

/** The synthetic root that gathers the hosts of one site. */
export function siteNodeId(siteId: string): string {
  return `${SITE_PREFIX}${siteId}`
}

export function serviceNodeId(hostName: string, serviceDescription: string): string {
  return `${hostName}${SEPARATOR}${serviceDescription}`
}

/** The stand-in for the services the backend did not send for this host. */
export function moreNodeId(hostName: string): string {
  return `${hostName}${MORE_SUFFIX}`
}

/**
 * A service node's own name — what the label under it reads, and what the
 * search matches against.
 */
export function serviceNameOf(nodeId: string): string {
  const separator = nodeId.indexOf(SEPARATOR)
  return separator === -1 ? '' : nodeId.slice(separator + SEPARATOR.length)
}

/** Whether this id names something that hangs off a host, rather than a host. */
export function isChildNodeId(nodeId: string): boolean {
  return nodeId.includes(SEPARATOR) && !nodeId.startsWith(SITE_PREFIX)
}
