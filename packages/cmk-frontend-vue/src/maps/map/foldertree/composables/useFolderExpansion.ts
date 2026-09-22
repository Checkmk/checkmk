/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How much of the folder tree is open.
 *
 * The list and the treemap are two drawings of one tree, so they share one
 * answer to that: an operator who opens a folder in the list and switches to
 * the map finds it open there too. Main is always opened, and its subfolders
 * only down to the depth the map's settings ask for -- so the tree opens on an
 * overview and is drilled into on demand, rather than dumping a whole site.
 */
import { type Ref, reactive, ref, watch } from 'vue'

import type { FolderTreeNode } from '@/maps/types/api'

export interface FolderExpansion {
  /** Paths of the nodes that are open. */
  expanded: ReadonlySet<string>
  /**
   * Bumped on every change. A drawing that has to relay out on a change reads
   * this rather than the set: the treemap watches several sources at once, and
   * Vue re-evaluates all of them whenever any one fires -- so a key built from
   * the set would be rebuilt on every state tick just to prove nothing moved.
   */
  version: Readonly<Ref<number>>
  toggle: (path: string) => void
  expandAll: () => void
  collapseAll: () => void
}

function folderPaths(node: FolderTreeNode, found: string[] = []): string[] {
  if (node.kind === 'folder') {
    found.push(node.path)
    node.children.forEach((child) => folderPaths(child, found))
  }
  return found
}

export function useFolderExpansion(
  root: Ref<FolderTreeNode | null>,
  expandDepth: () => number,
  mapName: () => string | null
): FolderExpansion {
  const expanded = reactive(new Set<string>())
  const version = ref(0)

  function changed(): void {
    version.value += 1
  }

  function seed(node: FolderTreeNode, depth: number, maxDepth: number): void {
    if (node.kind !== 'folder') {
      return
    }
    if (depth < maxDepth) {
      expanded.add(node.path)
    }
    node.children.forEach((child) => seed(child, depth + 1, maxDepth))
  }

  function reseed(node: FolderTreeNode): void {
    expanded.clear()
    expanded.add(node.path)
    node.children.forEach((child) => seed(child, 1, expandDepth()))
    changed()
  }

  // Reseed whenever the tree's identity changes, but keep the operator's own
  // opening and closing across the live state refreshes of the same tree. The
  // map is part of that identity: the view is reused when the map changes, and
  // two maps rooted the same way would otherwise share one expansion -- and the
  // second map's configured depth would never be applied.
  let seededFor = ''
  watch(
    [root, mapName],
    ([node]) => {
      if (!node) {
        return
      }
      const identity = `${mapName()}|${node.path}|${node.children.length}`
      if (identity === seededFor) {
        return
      }
      seededFor = identity
      reseed(node)
    },
    { immediate: true }
  )

  watch(expandDepth, () => {
    if (root.value) {
      reseed(root.value)
    }
  })

  return {
    expanded,
    version,
    toggle: (path) => {
      if (expanded.has(path)) {
        expanded.delete(path)
      } else {
        expanded.add(path)
      }
      changed()
    },
    expandAll: () => {
      if (root.value) {
        folderPaths(root.value).forEach((path) => expanded.add(path))
      }
      changed()
    },
    collapseAll: () => {
      // Main stays open, so the result is the top-level overview rather than a
      // single tile with everything hidden behind it.
      expanded.clear()
      if (root.value) {
        expanded.add(root.value.path)
      }
      changed()
    }
  }
}
