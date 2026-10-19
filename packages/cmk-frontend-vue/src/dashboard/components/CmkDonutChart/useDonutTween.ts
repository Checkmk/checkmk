/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { PieArcDatum } from 'd3-shape'
import { type Ref, onUnmounted, ref, shallowRef, watch } from 'vue'

import type { DonutSlice } from './types'

type Arc = PieArcDatum<DonutSlice>

export type SliceAngles = Map<string, Arc>

const DURATION_MS = 480

function ease(progress: number): number {
  return 1 - Math.pow(1 - progress, 3)
}

function prefersReducedMotion(): boolean {
  // Absent in jsdom, so treat "cannot tell" as "no preference expressed".
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

function interpolate(from: Arc, to: Arc, eased: number): Arc {
  return {
    ...to,
    startAngle: from.startAngle + (to.startAngle - from.startAngle) * eased,
    endAngle: from.endAngle + (to.endAngle - from.endAngle) * eased
  }
}

function collapsed(datum: Arc): Arc {
  return { ...datum, endAngle: datum.startAngle }
}

function sameGeometry(a: SliceAngles, b: SliceAngles): boolean {
  if (a.size !== b.size) {
    return false
  }
  for (const [key, datum] of a) {
    const other = b.get(key)
    if (
      other === undefined ||
      other.startAngle !== datum.startAngle ||
      other.endAngle !== datum.endAngle
    ) {
      return false
    }
  }
  return true
}

export interface DonutTween {
  /**
   * Angles to draw right now, easing towards `target` whenever it changes.
   *
   * The map outlives `target` by one animation: it still contains the leaving
   * slices while they collapse, and the caller has to render them.
   */
  angles: Ref<SliceAngles>
  /**
   * Keys that are only still drawn because they are collapsing. They are exit
   * animation rather than content, so the caller has to keep them out of reach.
   */
  leaving: Ref<ReadonlySet<string>>
}

export function useDonutTween(target: Ref<SliceAngles>): DonutTween {
  const displayed = ref<SliceAngles>(new Map(target.value)) as Ref<SliceAngles>
  const leavingKeys = shallowRef<ReadonlySet<string>>(new Set())

  let frame: number | null = null
  let from: SliceAngles = new Map()
  let to: SliceAngles = new Map()
  let leaving: Set<string> = new Set()
  // The last geometry asked for, without the collapsing leftovers `to` carries.
  let lastTarget: SliceAngles = new Map(target.value)
  let startedAt = 0

  function cancel(): void {
    if (frame !== null) {
      cancelAnimationFrame(frame)
      frame = null
    }
  }

  function settle(): void {
    cancel()
    leaving = new Set()
    leavingKeys.value = leaving
    to = new Map(target.value)
    displayed.value = new Map(target.value)
  }

  function step(now: number): void {
    const progress = Math.min(1, (now - startedAt) / DURATION_MS)
    const eased = ease(progress)

    const next: SliceAngles = new Map()
    for (const [key, toAngles] of to) {
      if (progress >= 1 && leaving.has(key)) {
        continue
      }
      next.set(key, interpolate(from.get(key)!, toAngles, eased))
    }
    displayed.value = next

    if (progress < 1) {
      frame = requestAnimationFrame(step)
      return
    }
    frame = null
    if (leaving.size > 0) {
      leaving = new Set()
      leavingKeys.value = leaving
    }
  }

  watch(target, (angles) => {
    const unchanged = sameGeometry(angles, lastTarget)
    lastTarget = new Map(angles)

    // A refresh that lands on the same geometry is no transition: take the
    // fresh values without replaying the animation over them.
    if (unchanged) {
      for (const [key, datum] of angles) {
        to.set(key, datum)
      }
      if (frame === null) {
        settle()
      }
      return
    }

    if (prefersReducedMotion()) {
      settle()
      return
    }

    const current = displayed.value
    from = new Map()
    to = new Map()
    leaving = new Set()

    for (const [key, targetDatum] of angles) {
      // A slice that is new starts as a sliver where it is about to open up.
      from.set(key, current.get(key) ?? collapsed(targetDatum))
      to.set(key, targetDatum)
    }
    for (const [key, currentDatum] of current) {
      if (angles.has(key)) {
        continue
      }
      leaving.add(key)
      from.set(key, currentDatum)
      to.set(key, collapsed(currentDatum))
    }

    leavingKeys.value = leaving
    cancel()
    startedAt = performance.now()
    frame = requestAnimationFrame(step)
  })

  onUnmounted(cancel)

  return { angles: displayed, leaving: leavingKeys }
}
