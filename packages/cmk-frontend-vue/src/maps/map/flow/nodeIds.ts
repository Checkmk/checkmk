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
const FOLD_SUFFIX = `${SEPARATOR}__fold__`

/** The kinds of node a flow map draws. */
export type FlowNodeKind = 'host' | 'service' | 'more' | 'site' | 'fold'

interface KindTraits {
  /** Drawn and laid out like a host: a circle with a ring, placed in the parent tree. */
  hostShaped: boolean
  /** A monitored object, which can be selected, hovered for details and given a menu. */
  monitored: boolean
  /** The operator can move it, and the map remembers where they put it. */
  draggable: boolean
  /** Drawn at every zoom level, not only once the services are on show. */
  coarse: boolean
}

/** What each kind of node is, so the rules about it live in one place. */
export const KIND_TRAITS: Readonly<Record<FlowNodeKind, Readonly<KindTraits>>> = {
  host: { hostShaped: true, monitored: true, draggable: true, coarse: true },
  fold: { hostShaped: true, monitored: false, draggable: false, coarse: true },
  site: { hostShaped: false, monitored: false, draggable: true, coarse: true },
  service: { hostShaped: false, monitored: true, draggable: false, coarse: false },
  more: { hostShaped: false, monitored: true, draggable: false, coarse: false }
}

/** The synthetic root that gathers the hosts of one site. */
export function siteNodeId(siteId: string): string {
  return `${SITE_PREFIX}${siteId}`
}

export function isSiteNodeId(nodeId: string): boolean {
  return nodeId.startsWith(SITE_PREFIX)
}

export function serviceNodeId(hostName: string, serviceDescription: string): string {
  return `${hostName}${SEPARATOR}${serviceDescription}`
}

/** The fold for the hosts not drawn under a host or a site root. */
export function foldNodeId(parentId: string): string {
  return `${parentId}${FOLD_SUFFIX}`
}

export function isFoldNodeId(nodeId: string): boolean {
  return nodeId.endsWith(FOLD_SUFFIX)
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
