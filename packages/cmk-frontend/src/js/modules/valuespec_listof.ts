/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// The index of the ListOf entry containing the element, e.g. its delete button. Finding it in the
// DOM also works for entries added from the prototype, which only renames the IDs of the entry.
export function listof_entry_index(element: HTMLElement, varprefix: string): string {
  const prefix = varprefix + '_entry_'
  for (let node: HTMLElement | null = element; node; node = node.parentElement) {
    if (node.id.startsWith(prefix)) {
      return node.id.slice(prefix.length)
    }
  }
  throw new Error(`Failed to find the entry of ${varprefix} containing the element`)
}
