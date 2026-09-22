/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * A folder tree's leaves, as the objects the rest of the map view speaks in.
 *
 * A folder tree has nothing placed on it, and its leaves never enter the state
 * stream: the flat host list is empty by design and services are fetched only
 * when an operator drills into a host. So a hover card or a slide-in opened from
 * a leaf is handed both a synthesised object and the state the tree node already
 * carries, rather than looking the state up by id and finding nothing.
 */
import type { FolderTreeNode, MapElement, ObjectState } from '@/maps/types/api'
import { monitoringObjectId, newMonitoringElement, newObjectState } from '@/maps/utils/model'

// What a leaf stands for. A host leaf is named by its own title; a service leaf
// is named by its title on the host it was reached through.
function leafTarget(
  node: FolderTreeNode,
  host: string | null
): { host: string; service: string | null } {
  return host === null ? { host: node.title, service: null } : { host, service: node.title }
}

/** The leaf as a map object. Pass `host` for a service leaf, `null` for a host. */
export function folderNodeToElement(node: FolderTreeNode, host: string | null): MapElement {
  const target = leafTarget(node, host)
  return newMonitoringElement(target.host, target.service)
}

/** The state the leaf already knows about itself. */
export function folderNodeToState(node: FolderTreeNode, host: string | null): ObjectState {
  const target = leafTarget(node, host)
  return newObjectState({
    object_id: monitoringObjectId(target.host, target.service),
    type: target.service === null ? 'host' : 'service',
    state: node.state,
    output: node.output,
    acknowledged: node.acknowledged,
    in_downtime: node.in_downtime,
    stale: node.stale,
    site_id: node.site_id ?? null,
    last_state_change: node.last_state_change ?? null,
    services_summary: node.services_summary ?? null
  })
}

/** A host in a folder, as a command about the folder needs it. */
export interface FolderHost {
  host: string
  site: string | null
  /** The state the tree knows the host by. */
  state: string
}

/** Every host in a folder, for a command that applies to the folder as a whole. */
export function folderHosts(node: FolderTreeNode, includeSubfolders: boolean): FolderHost[] {
  const found = new Map<string, FolderHost>()
  const walk = (folder: FolderTreeNode): void => {
    for (const child of folder.children) {
      if (child.kind === 'host') {
        if (!found.has(child.title)) {
          found.set(child.title, {
            host: child.title,
            site: child.site_id ?? null,
            state: child.state
          })
        }
      } else if (includeSubfolders && child.kind === 'folder') {
        walk(child)
      }
    }
  }
  walk(node)
  return [...found.values()]
}
