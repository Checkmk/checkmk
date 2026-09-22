/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What a folder tree shows under the operator's search and problems filter.
 *
 * The list and the treemap are two drawings of the same tree, so both ask these
 * same questions -- is this subtree still worth showing, which of a host's
 * services survive, how many hosts are left -- and therefore always agree on
 * what is on screen.
 */
import type { FolderTreeNode } from '@/maps/types/api'
import {
  type FilterField,
  type FilterTerm,
  matchesFilterTerms,
  parseFilterTerms
} from '@/maps/utils/objectFilter'
import { type ProblemSeverity, isProblemState } from '@/maps/utils/problemState'

export type { FilterTerm, ProblemSeverity }

/** Everything that decides whether a node is on screen. */
export interface FolderQuery {
  terms: FilterTerm[]
  problemsOnly: boolean
  /** How bad a state has to be to count as a problem. */
  severity: ProblemSeverity
  /**
   * Hosts the server's service search matched. A service-scoped term is answered
   * there rather than here: service leaves are lazily loaded, so the browser
   * cannot know which hosts run a matching service.
   */
  matchedHosts: Set<string>
}

// The foldertree only ever holds hosts and services, so only the `h:`/`s:`
// operators (and bare text) are meaningful here -- hg:/sg:/id: are dropped,
// mirroring how the flow map drops the fields its objects can't carry. The
// MapSearch UI already hides those operators via `:exclude-prefixes`.
const FOLDER_FIELDS = new Set<FilterField>(['host', 'service', 'any'])

/** Parse the MapSearch string with the shared quicksearch grammar, keeping
 *  only the host/service-scoped (and bare) terms. */
export function parseFolderQuery(raw: string): FilterTerm[] {
  return parseFilterTerms(raw).filter((term) => FOLDER_FIELDS.has(term.field))
}

/** Whether the query actually constrains anything. */
export function isFilterActive(query: FolderQuery): boolean {
  return query.problemsOnly || query.terms.length > 0
}

const hasServiceTerm = (terms: FilterTerm[]): boolean =>
  terms.some((term) => term.field === 'service')

// Host/any terms must all match the host name; service-scoped terms don't decide
// which hosts show -- they constrain a host's service leaves (filtered separately).
function hostNameMatches(hostName: string, terms: FilterTerm[]): boolean {
  if (terms.length === 0) {
    return true
  }
  const name = hostName.toLowerCase()
  return terms.every((term) => term.field === 'service' || name.includes(term.needle))
}

// Whether a host shows under the active query. With a service-scoped term the
// answer is authoritative from the server's matched hosts (host terms applied
// there too): a host without a matching service drops out, so a `s:` query
// narrows to hosts that actually run it instead of listing the whole site to
// drill into one by one. Without a service term it's the instant client-side
// host-name match, plus any server service-hit for bare terms.
function hostVisible(hostName: string, query: FolderQuery): boolean {
  if (hasServiceTerm(query.terms)) {
    return query.matchedHosts.has(hostName)
  }
  return hostNameMatches(hostName, query.terms) || query.matchedHosts.has(hostName)
}

// A service leaf matches when every term is satisfied -- host terms against its
// host name, service terms against its description, bare terms against either.
// Reuses the shared quicksearch matcher (one place for the AND/substring rules);
// the host name is supplied by the caller because service leaves don't carry it.
export function serviceMatches(
  hostName: string,
  serviceName: string,
  terms: FilterTerm[]
): boolean {
  return matchesFilterTerms(terms, (field) =>
    field === 'host' ? [hostName] : field === 'service' ? [serviceName] : [hostName, serviceName]
  )
}

// A folder's own name only counts as a hit for unscoped queries (no h:/s:): then
// every bare term must match the folder name (searching "Datacenters" reveals its
// whole subtree). A scoped query never matches on a folder name.
function folderNameMatches(folderName: string, terms: FilterTerm[]): boolean {
  if (terms.length === 0) {
    return false
  }
  const name = folderName.toLowerCase()
  return terms.every((term) => term.field === 'any' && name.includes(term.needle))
}

/** Whether a node is itself a full query hit, so its whole subtree counts as
 *  matching (propagated down via the `ancestorMatched` flag). A host is a full
 *  hit only for host/bare queries -- a service-scoped term must be checked against
 *  the actual service leaves, so it does not blanket-reveal a host's services. */
export function selfMatches(node: FolderTreeNode, terms: FilterTerm[]): boolean {
  if (node.kind === 'folder') {
    return folderNameMatches(node.title, terms)
  }
  if (node.kind === 'host') {
    return !hasServiceTerm(terms) && hostNameMatches(node.title, terms)
  }
  return false
}

/** Combined "Problems only" + search visibility for a subtree of store-tree nodes
 *  (folders and hosts). Service leaves are lazily loaded and live outside
 *  `children`, so the caller filters them with {@link serviceVisible} using the
 *  owning host's name. `ancestorMatched` is set once a containing folder/host
 *  already matched, so its whole subtree counts as matching. */
export function subtreeVisible(
  node: FolderTreeNode,
  query: FolderQuery,
  ancestorMatched = false
): boolean {
  const passesProblems = (state: string): boolean =>
    !query.problemsOnly || isProblemState(state, query.severity)
  if (node.kind === 'host') {
    return (ancestorMatched || hostVisible(node.title, query)) && passesProblems(node.state)
  }
  if (node.kind === 'service') {
    // Reached only when a service leaf has no host context; match its
    // description against the non-host terms as a best effort.
    const matched = ancestorMatched || serviceMatches('', node.title, query.terms)
    return matched && passesProblems(node.state)
  }
  const selfMatch = ancestorMatched || folderNameMatches(node.title, query.terms)
  if (node.children.some((child) => subtreeVisible(child, query, selfMatch))) {
    return true
  }
  return selfMatch && !query.problemsOnly && node.children.length === 0
}

/**
 * Paths of the hosts a containing folder already matched by name, so their
 * service leaves count as matching too.
 *
 * The list carries this down its walk as `ancestorMatched`. The treemap has no
 * walk to carry it on -- it asks for a host's services from two places, neither
 * of which knows how the host was reached -- so it looks the same answer up
 * here instead, and both drawings reveal the same services under a folder hit.
 */
export function hostsMatchedByAncestor(
  root: FolderTreeNode,
  terms: FilterTerm[]
): ReadonlySet<string> {
  const found = new Set<string>()
  if (terms.length === 0) {
    return found
  }
  const walk = (node: FolderTreeNode, ancestorMatched: boolean): void => {
    if (node.kind === 'host') {
      if (ancestorMatched) {
        found.add(node.path)
      }
      return
    }
    const matched = ancestorMatched || selfMatches(node, terms)
    node.children.forEach((child) => walk(child, matched))
  }
  walk(root, false)
  return found
}

/** Visibility of a single lazily-loaded service leaf under `hostName`, combining
 *  the search terms (with host context) and the problems-only toggle. */
export function serviceVisible(
  hostName: string,
  node: FolderTreeNode,
  query: FolderQuery,
  ancestorMatched = false
): boolean {
  const matched = ancestorMatched || serviceMatches(hostName, node.title, query.terms)
  return matched && (!query.problemsOnly || isProblemState(node.state, query.severity))
}

/** A host's lazily-loaded service leaves filtered to the active query -- shared by
 *  the list and the treemap so both show the same set under a host. */
export function visibleServices(
  hostName: string,
  services: FolderTreeNode[],
  query: FolderQuery,
  hostMatched: boolean
): FolderTreeNode[] {
  if (!isFilterActive(query)) {
    return services
  }
  return services.filter((service) => serviceVisible(hostName, service, query, hostMatched))
}

/** How many hosts survive the filter, and how their problems break down --
 *  so the summary counts what is on screen rather than the whole tree. */
export interface HostStats {
  hosts: number
  counts: Record<string, number>
}

export function visibleHostStats(
  node: FolderTreeNode,
  query: FolderQuery,
  ancestorMatched = false
): HostStats {
  if (node.kind === 'service') {
    return { hosts: 0, counts: {} }
  }
  if (node.kind === 'host') {
    if (!subtreeVisible(node, query, ancestorMatched)) {
      return { hosts: 0, counts: {} }
    }
    return { hosts: 1, counts: isProblemState(node.state) ? { [node.state]: 1 } : {} }
  }
  const selfMatch = ancestorMatched || selfMatches(node, query.terms)
  const counts: Record<string, number> = {}
  let hosts = 0
  for (const child of node.children) {
    const stats = visibleHostStats(child, query, selfMatch)
    hosts += stats.hosts
    for (const [state, count] of Object.entries(stats.counts)) {
      counts[state] = (counts[state] ?? 0) + count
    }
  }
  return { hosts, counts }
}
