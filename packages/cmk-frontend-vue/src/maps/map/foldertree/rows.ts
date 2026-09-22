/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The folder tree as a flat list of rows.
 *
 * The list has to scale to a site with a hundred thousand hosts, so it is
 * windowed: only the rows the viewport covers are in the DOM. Windowing needs a
 * flat, indexable list, so the visible part of the tree -- what is expanded,
 * what survives the filter -- is projected into one here, and the row component
 * stays purely presentational.
 */
import type { FolderTreeNode } from '@/maps/types/api'

import { type FolderQuery, selfMatches } from './filter'

/** One row. `note` rows are a host's loading/error/no-services placeholders,
 *  which keep the host as their node so depth and key still line up. */
export interface FlatRow {
  key: string
  node: FolderTreeNode
  depth: number
  isOpen: boolean
  isExpandable: boolean
  /** The owning host, for a service row. */
  hostName?: string | undefined
  note?: 'loading' | 'error' | 'empty'
}

interface RowSource {
  query: FolderQuery
  expanded: ReadonlySet<string>
  /** Whether hosts can be drilled into at all. */
  showServices: boolean
  /** A host's service leaves that survive the filter. */
  servicesOf: (host: FolderTreeNode, hostMatched: boolean) => FolderTreeNode[]
  /** A folder's child nodes that survive the filter. */
  childrenOf: (folder: FolderTreeNode, folderMatched: boolean) => FolderTreeNode[]
  serviceLoading: ReadonlySet<string>
  serviceError: ReadonlySet<string>
}

/**
 * Project the expanded, filtered tree into rows -- a folder's own rows before
 * its subfolders, the same order the tree reads in. A text search opens every
 * folder on the way to a match, so the hit shows without drilling for it.
 */
export function flattenTree(root: FolderTreeNode, source: RowSource): FlatRow[] {
  const rows: FlatRow[] = []
  const terms = source.query.terms
  const searching = terms.length > 0

  const isExpandable = (node: FolderTreeNode): boolean =>
    node.kind === 'folder' ||
    (node.kind === 'host' && source.showServices) ||
    node.children.length > 0

  const isOpen = (node: FolderTreeNode, matched: boolean): boolean => {
    if (source.expanded.has(node.path)) {
      return true
    }
    if (!searching) {
      return false
    }
    if (node.kind === 'folder') {
      return true
    }
    // A host that only survived the search through one of its services opens to
    // reveal it; a host matched by its own name stays shut.
    return (
      node.kind === 'host' &&
      source.showServices &&
      !selfMatches(node, terms) &&
      source.servicesOf(node, matched).length > 0
    )
  }

  const walk = (
    node: FolderTreeNode,
    depth: number,
    ancestorMatched: boolean,
    hostName?: string
  ) => {
    const matched = ancestorMatched || selfMatches(node, terms)
    const open = isOpen(node, matched)
    rows.push({
      key: `${node.path}:${node.kind}:${node.title}`,
      node,
      depth,
      isOpen: open,
      isExpandable: isExpandable(node),
      hostName
    })
    if (!open) {
      return
    }

    if (node.kind !== 'host') {
      for (const child of source.childrenOf(node, matched)) {
        walk(child, depth + 1, matched)
      }
      return
    }

    const note = (kind: 'loading' | 'error' | 'empty'): void => {
      rows.push({
        key: `${node.path}:${kind}`,
        node,
        depth: depth + 1,
        isOpen: false,
        isExpandable: false,
        note: kind
      })
    }
    if (source.serviceLoading.has(node.title)) {
      return note('loading')
    }
    if (source.serviceError.has(node.title)) {
      return note('error')
    }
    const services = source.servicesOf(node, matched)
    if (services.length === 0) {
      return note('empty')
    }
    for (const service of services) {
      walk(service, depth + 1, matched, node.title)
    }
  }

  walk(root, 0, false)
  return rows
}
