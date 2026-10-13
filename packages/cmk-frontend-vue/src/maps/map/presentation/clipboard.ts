/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { PresentationElement } from '@/maps/types/api'

import { type ElementById, isConnectorShape } from './connectors'
import { clone, newElementId } from './elements'

/** How far a copy is offset from its original, in slide units. */
const PASTE_OFFSET = 24

/**
 * A self-contained set of elements: the ones that were selected (``tops``) plus
 * every group member they carry along, so a group survives a copy as a unit.
 */
export interface ElementSelection {
  els: PresentationElement[]
  tops: string[]
}

/** Snapshot a selection for duplicating or for the clipboard. */
export function collectWithChildren(topIds: string[], byId: ElementById): ElementSelection {
  const seen = new Set<string>()
  const els: PresentationElement[] = []
  const walk = (id: string): void => {
    if (seen.has(id)) {
      return
    }
    seen.add(id)
    const el = byId(id)
    if (!el) {
      return
    }
    els.push(clone(el))
    if (el.kind === 'group') {
      el.children.forEach(walk)
    }
  }
  topIds.forEach(walk)
  return { els, tops: topIds.filter((id) => byId(id)) }
}

/**
 * Re-id a snapshot (fresh ids, group children and connector ends remapped to
 * them), offset it and stack it on top. Returns the copies plus the new ids of
 * the formerly-top elements, which is what the caller selects afterwards.
 */
export function instantiate(
  source: ElementSelection,
  nextZ: number
): { copies: PresentationElement[]; newTops: string[] } {
  const idMap = new Map<string, string>()
  const copies = source.els.map((el) => {
    const copy = clone(el)
    copy.id = newElementId(el.kind)
    idMap.set(el.id, copy.id)
    return copy
  })
  // An id inside the snapshot follows its copy; one outside it (a connector
  // docked to an element that was not copied) keeps pointing at the original.
  const remap = (id: string | null | undefined): string | null =>
    id ? (idMap.get(id) ?? id) : null
  copies.forEach((copy, i) => {
    copy.x += PASTE_OFFSET
    copy.y += PASTE_OFFSET
    copy.z = nextZ + i
    if (copy.kind === 'group') {
      copy.children = copy.children.map((child) => idMap.get(child) ?? child)
    } else if (isConnectorShape(copy)) {
      copy.start_ref = remap(copy.start_ref)
      copy.end_ref = remap(copy.end_ref)
    }
  })
  const newTops = source.tops.map((id) => idMap.get(id)).filter((id): id is string => !!id)
  return { copies, newTops }
}
