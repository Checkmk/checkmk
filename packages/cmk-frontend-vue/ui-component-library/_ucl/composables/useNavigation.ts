/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { roots } from '@ucl/components/'
import { type Component, type Ref, ref } from 'vue'

import { type Folder, Page, toSlug } from '../types/page'

export interface NavPage {
  type: 'page'
  name: string
  path: string
  component: Component<{ screenshotMode: boolean }>
}

export interface NavFolder {
  type: 'folder'
  name: string
  path: string
  isOpen: Ref<boolean>
  children: Array<NavPage | NavFolder>
}

export type NavItem = NavPage | NavFolder

function toNavItem(item: Page | Folder, parentPath: string): NavItem {
  const itemPath = `${parentPath}/${toSlug(item.name)}`
  if (item instanceof Page) {
    return {
      type: 'page' as const,
      name: item.name,
      path: itemPath,
      component: item.component
    }
  }
  return {
    type: 'folder' as const,
    name: item.name,
    path: itemPath,
    isOpen: ref(item.defaultOpen),
    children: item.pages
      .map((child) => toNavItem(child, itemPath))
      .sort((a, b) => a.name.localeCompare(b.name))
  }
}

// Top-level roots keep their authored order (so Foundations lands above
// Components regardless of name); nested folders sort alphabetically.
const navTrees = roots.map((root) => toNavItem(root, '')) as NavFolder[]

export function useNavigation() {
  function openPathToRoute(routePath: string) {
    const segments = routePath.split('/').filter(Boolean)
    let items: NavItem[] = navTrees

    for (const segment of segments) {
      const folder = items.find(
        (item): item is NavFolder => item.type === 'folder' && toSlug(item.name) === segment
      )
      if (folder) {
        folder.isOpen.value = true
        items = folder.children
      } else {
        break
      }
    }
  }

  return {
    navTrees,
    openPathToRoute
  }
}
