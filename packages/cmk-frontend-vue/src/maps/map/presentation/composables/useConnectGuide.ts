/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, ref, watch } from 'vue'

import type { PresentationElement } from '@/maps/types/api'

import { type BindableElement, isBindable, isUnboundSlot } from '../binding'
import { type ElementById, elementBounds } from '../connectors'
import type { Box } from '../geometry'

// The connect-data walkthrough: after designing a slide (or applying a
// template), every unbound data slot is visited in reading order and bound via
// the shared binding form. The guide only steers which slot is current — all
// mutations stay on the canvas's mutate() pipeline.
//
// Binding a host does NOT auto-advance: the slot stays current so the operator
// can still pick a service and label. Advancing is always explicit (Next/Skip,
// badge click), which keeps the flow predictable.

// Reading order: rows top→bottom (with a tolerance so slightly staggered tiles
// count as one row), left→right within a row.
const ROW_TOLERANCE = 80

function readingOrder(a: { x: number; y: number }, b: { x: number; y: number }): number {
  const rowA = Math.floor(a.y / ROW_TOLERANCE)
  const rowB = Math.floor(b.y / ROW_TOLERANCE)
  return rowA - rowB || a.x - b.x
}

export function useConnectGuide(elements: () => PresentationElement[], byId: ElementById) {
  const active = ref(false)
  const currentId = ref<string | null>(null)
  // Slot ids in the reading order captured at entry. Binding a slot must not
  // renumber the rest — badges and the popover title stay stable across the
  // whole walkthrough. Slots created mid-session append at the end.
  const slotOrder = ref<string[]>([])

  // Sort on the real on-slide bounds — a connector's own x/y is vestigial.
  function bounds(el: PresentationElement): Box {
    return elementBounds(el, byId)
  }

  const unbound = computed(() => elements().filter(isUnboundSlot))
  // The badge on the palette's connect button reads this for the whole edit
  // session, so it must not depend on the reading-order sort — that reads every
  // slot's on-slide bounds and would re-run on every pointer move.
  const unboundCount = computed(() => unbound.value.length)
  const slots = computed(() =>
    [...unbound.value].sort((a, b) => readingOrder(bounds(a), bounds(b)))
  )

  watch(slots, (list) => {
    if (!active.value) {
      return
    }
    for (const s of list) {
      if (!slotOrder.value.includes(s.id)) {
        slotOrder.value.push(s.id)
      }
    }
  })

  // Every slot of the session (bound ones included) with its stable number —
  // the overlay shows bound slots as checked instead of dropping them.
  const sessionSlots = computed(() =>
    slotOrder.value
      .map((id, i) => {
        const el = byId(id)
        return el && isBindable(el) ? { el, n: i + 1, bound: !isUnboundSlot(el) } : null
      })
      .filter((s): s is { el: BindableElement; n: number; bound: boolean } => s !== null)
  )

  // Progress derives from the session order so slots created mid-session
  // count toward the total instead of pushing the bar past 100%.
  const totalCount = computed(() => sessionSlots.value.length)
  const boundCount = computed(() => sessionSlots.value.filter((s) => s.bound).length)

  function slotNumber(id: string): number | null {
    const i = slotOrder.value.indexOf(id)
    return i === -1 ? null : i + 1
  }

  // The current slot survives being bound (unlike `slots`) so the popover can
  // stay open for the service/label step.
  const current = computed<BindableElement | null>(() => {
    const el = byId(currentId.value)
    return el && isBindable(el) ? el : null
  })
  const currentBound = computed(() => !!current.value && !isUnboundSlot(current.value))

  function enter(): void {
    slotOrder.value = slots.value.map((s) => s.id)
    currentId.value = slots.value[0]?.id ?? null
    active.value = slotOrder.value.length > 0
  }

  function exit(): void {
    active.value = false
    currentId.value = null
  }

  function goTo(id: string): void {
    const el = byId(id)
    if (el && isUnboundSlot(el)) {
      currentId.value = id
    }
  }

  // Next/prev move through the remaining unbound slots relative to the current
  // element's reading-order position — also when the current one is already
  // bound (and therefore no longer part of `slots`). With nothing left to
  // visit, Next finishes the walkthrough.
  function step(dir: 1 | -1): void {
    const list = slots.value
    if (!list.length) {
      exit()
      return
    }
    const cur = current.value
    const idx = list.findIndex((s) => s.id === currentId.value)
    if (idx !== -1) {
      // Skipping forward off the only remaining slot ends the walkthrough —
      // cycling back onto the slot just skipped would trap the operator.
      // Prev stays put instead of tearing the session down.
      if (list.length === 1) {
        if (dir === 1) {
          exit()
        }
        return
      }
      currentId.value = list[(idx + dir + list.length) % list.length]?.id ?? null
      return
    }
    if (!cur) {
      currentId.value = list[0]?.id ?? null
      return
    }
    const curBox = bounds(cur)
    const after = list.filter((s) => readingOrder(curBox, bounds(s)) < 0)
    const before = list.filter((s) => readingOrder(curBox, bounds(s)) >= 0)
    const target =
      dir === 1 ? (after[0] ?? list[0]) : (before[before.length - 1] ?? list[list.length - 1])
    currentId.value = target?.id ?? null
  }

  function next(): void {
    step(1)
  }
  function prev(): void {
    step(-1)
  }

  // Only a deleted current element retargets the guide; with nothing bindable
  // left at all the walkthrough ends. Sync flush so a delete that is undone in
  // the same tick can't slip past the pre-flush change comparison.
  watch(
    current,
    (c) => {
      if (!active.value || c) {
        return
      }
      if (slots.value.length) {
        currentId.value = slots.value[0]?.id ?? null
      } else {
        exit()
      }
    },
    { flush: 'sync' }
  )

  return {
    active,
    slots,
    sessionSlots,
    slotNumber,
    unboundCount,
    boundCount,
    totalCount,
    current,
    currentBound,
    currentId,
    enter,
    exit,
    goTo,
    next,
    prev
  }
}
