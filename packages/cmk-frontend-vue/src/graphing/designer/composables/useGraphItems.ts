/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed, ref } from 'vue'

import { collectTransitiveDependents } from '../calculation/formula'
import type { DesignerItem } from '../drafts'
import {
  type FormulaDraft,
  type FormulaItem,
  type ItemId,
  type SingleLineItem,
  isFormula,
  isSingleLine
} from '../types'

const CHAR_CODE_A = 'A'.charCodeAt(0)

/** Spreadsheet-style id for a 0-based index: 0 -> A, 25 -> Z, 26 -> AA, ... */
function idFromIndex(index: number): ItemId {
  let n = index
  let id = ''
  do {
    id = String.fromCharCode(CHAR_CODE_A + (n % 26)) + id
    n = Math.floor(n / 26) - 1
  } while (n >= 0)
  return id
}

/** Inverse of {@link idFromIndex}: A -> 0, Z -> 25, AA -> 26, ... */
function indexFromId(id: ItemId): number {
  let n = 0
  for (const char of id) {
    n = n * 26 + (char.charCodeAt(0) - CHAR_CODE_A + 1)
  }
  return n - 1
}

/** Id after the highest one in use; a removed id only recurs once nothing above it remains. */
function nextId(items: readonly DesignerItem[]): ItemId {
  const highest = items.reduce((max, item) => Math.max(max, indexFromId(item.id)), -1)
  return idFromIndex(highest + 1)
}

/** Picks the least-used palette color, preferring earlier entries on ties (unused counts as zero). */
function nextColor(items: readonly DesignerItem[], palette: readonly string[]): string {
  if (palette.length === 0) {
    return '#000000'
  }
  const counts = new Map<string, number>(palette.map((color) => [color, 0]))
  for (const item of items.filter(isSingleLine)) {
    const count = counts.get(item.color)
    if (count !== undefined) {
      counts.set(item.color, count + 1)
    }
  }
  return palette.reduce((best, color) => (counts.get(color)! < counts.get(best)! ? color : best))
}

/** The row fields every single-line item shares; `color` is skipped on multi-line rows. */
export type SharedRowPatch = Partial<
  Pick<SingleLineItem, 'title' | 'line_type' | 'mirrored' | 'visible' | 'color'>
>

export interface GraphItemsStore {
  items: ComputedRef<readonly DesignerItem[]>
  /** Id the next added item will get. */
  nextId: ComputedRef<ItemId>
  /** Default color for the next added item. */
  nextColor: ComputedRef<string>
  /** Add a new formula item; returns its assigned id. */
  addFormula: (draft: FormulaDraft) => ItemId
  /** Replace an existing formula item's AST, title and color, keeping line style/visibility. */
  updateFormula: (id: ItemId, draft: FormulaDraft) => void
  /** Add any item; the factory receives the assigned id. Returns that id. */
  addItem: (create: (id: ItemId) => DesignerItem) => ItemId
  /** Update an item's shared row fields; `color` is only applied to single-line items. */
  patch: (id: ItemId, patch: SharedRowPatch) => void
  /** Swap an existing item for `item` (matched by id), e.g. after a type switch. */
  replace: (item: DesignerItem) => void
  /** Swap every item for `replacements`, discarding the ids in use. */
  replaceAll: (replacements: readonly DesignerItem[]) => void
  /** Copy each given row, inserting the copy right below it. Returns the new ids. */
  clone: (ids: readonly ItemId[]) => ItemId[]
  /** Move the row at `from` to position `to`. */
  move: (from: number, to: number) => void
  remove: (id: ItemId) => void
  removeMany: (ids: readonly ItemId[]) => void
  setVisibility: (ids: ItemId[], visible: boolean) => void
  /** Formula items whose refs (transitively) reach `id` — they break if `id` is deleted. */
  dependentsOf: (id: ItemId) => FormulaItem[]
}

/**
 * @param palette Default metric colors to use.
 * @param seed Pre-existing items (e.g. when editing an existing graph).
 */
export function useGraphItems(
  palette: readonly string[],
  seed: readonly DesignerItem[] = []
): GraphItemsStore {
  const items = ref<DesignerItem[]>([...seed])

  function requireFormula(id: ItemId): FormulaItem {
    const item = items.value.find((candidate) => candidate.id === id)
    if (item === undefined || !isFormula(item)) {
      throw new Error(`No formula item with id "${id}"`)
    }
    return item
  }

  function requireKnown(ids: readonly ItemId[]): void {
    const known = new Set(items.value.map((item) => item.id))
    for (const id of ids) {
      if (!known.has(id)) {
        throw new Error(`No item with id "${id}"`)
      }
    }
  }

  function addFormula(draft: FormulaDraft): ItemId {
    const id = nextId(items.value)
    items.value = [
      ...items.value,
      { id, line_type: 'line', mirrored: false, visible: true, ...draft }
    ]
    return id
  }

  function updateFormula(id: ItemId, draft: FormulaDraft): void {
    const existing = requireFormula(id)
    items.value = items.value.map((item) =>
      item.id === id
        ? { ...existing, ast: draft.ast, title: draft.title, color: draft.color }
        : item
    )
  }

  function addItem(create: (id: ItemId) => DesignerItem): ItemId {
    const id = nextId(items.value)
    const item = create(id)
    if (item.id !== id) {
      throw new Error(`Factory must keep the assigned id "${id}", got "${item.id}"`)
    }
    items.value = [...items.value, item]
    return id
  }

  function patch(id: ItemId, patchValues: SharedRowPatch): void {
    requireKnown([id])
    const { color, ...shared } = patchValues
    items.value = items.value.map((item) => {
      if (item.id !== id) {
        return item
      }
      const updated = { ...item, ...shared }
      return color !== undefined && isSingleLine(updated) ? { ...updated, color } : updated
    })
  }

  function replace(item: DesignerItem): void {
    requireKnown([item.id])
    items.value = items.value.map((existing) => (existing.id === item.id ? item : existing))
  }

  function replaceAll(replacements: readonly DesignerItem[]): void {
    items.value = [...replacements]
  }

  function clone(ids: readonly ItemId[]): ItemId[] {
    requireKnown(ids)
    const idSet = new Set(ids)
    const all = [...items.value]
    const next: DesignerItem[] = []
    const created: ItemId[] = []
    for (const item of items.value) {
      next.push(item)
      if (idSet.has(item.id)) {
        const copy = { ...item, id: nextId(all) }
        all.push(copy)
        next.push(copy)
        created.push(copy.id)
      }
    }
    items.value = next
    return created
  }

  function move(from: number, to: number): void {
    const next = [...items.value]
    const [moved] = next.splice(from, 1)
    if (moved === undefined) {
      throw new Error(`No item at index ${from}`)
    }
    next.splice(to, 0, moved)
    items.value = next
  }

  function remove(id: ItemId): void {
    if (!items.value.some((item) => item.id === id)) {
      throw new Error(`No item with id "${id}"`)
    }
    items.value = items.value.filter((item) => item.id !== id)
  }

  function removeMany(ids: readonly ItemId[]): void {
    requireKnown(ids)
    const idSet = new Set(ids)
    items.value = items.value.filter((item) => !idSet.has(item.id))
  }

  function setVisibility(ids: ItemId[], visible: boolean): void {
    const idSet = new Set(ids)
    items.value = items.value.map((item) => (idSet.has(item.id) ? { ...item, visible } : item))
  }

  function dependentsOf(id: ItemId): FormulaItem[] {
    const formulas = items.value.filter(isFormula)
    const reached = collectTransitiveDependents(formulas, id)
    return formulas.filter((formula) => reached.has(formula.id))
  }

  return {
    items: computed(() => Object.freeze([...items.value])),
    nextId: computed(() => nextId(items.value)),
    nextColor: computed(() => nextColor(items.value, palette)),
    addFormula,
    updateFormula,
    addItem,
    patch,
    replace,
    replaceAll,
    clone,
    move,
    remove,
    removeMany,
    setVisibility,
    dependentsOf
  }
}
