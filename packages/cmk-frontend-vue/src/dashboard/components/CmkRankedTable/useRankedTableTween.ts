/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onUnmounted, shallowRef, watch } from 'vue'

/** What one bar cell settles on: its bar width and the value text beside it. */
export interface BarTarget {
  percent: number
  text: string
  unit: string | undefined
}

/** What one bar cell shows right now. */
export interface BarFrame {
  percent: number
  text: string
}

const DURATION_MS = 200

const PLAIN_NUMBER = /^-?\d+(\.\d+)?$/

function ease(progress: number): number {
  return 1 - Math.pow(1 - progress, 3)
}

function prefersReducedMotion(): boolean {
  // Absent in jsdom, so treat "cannot tell" as "no preference expressed".
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

function decimals(text: string): number {
  return text.split('.')[1]?.length ?? 0
}

interface Shown {
  percent: number
  /** The number on display, while the text is a plain one that can be counted from. */
  count: number | undefined
  decimals: number
  unit: string | undefined
}

interface Leg {
  from: Shown
  to: BarTarget
  /** Whether the value counts towards its target instead of switching to it. */
  counts: boolean
  decimals: number
}

function shownOf(target: BarTarget): Shown {
  const count = PLAIN_NUMBER.test(target.text) ? Number(target.text) : undefined
  return { percent: target.percent, count, decimals: decimals(target.text), unit: target.unit }
}

function sameTargets(a: Map<string, BarTarget>, b: Map<string, BarTarget>): boolean {
  if (a.size !== b.size) {
    return false
  }
  for (const [key, target] of a) {
    const other = b.get(key)
    if (
      other === undefined ||
      other.percent !== target.percent ||
      other.text !== target.text ||
      other.unit !== target.unit
    ) {
      return false
    }
  }
  return true
}

function countAt(leg: Leg, eased: number): number {
  const from = leg.from.count!
  return from + (Number(leg.to.text) - from) * eased
}

function frameAt(leg: Leg, eased: number, done: boolean): BarFrame {
  const percent = leg.from.percent + (leg.to.percent - leg.from.percent) * eased
  if (done || !leg.counts) {
    return { percent, text: leg.to.text }
  }
  // As many decimals as either end has, so that the first frame shows the old value as it was.
  return { percent, text: countAt(leg, eased).toFixed(leg.decimals) }
}

/**
 * Bar widths and values to draw right now, keyed like `targets`.
 *
 * The first targets are drawn as they are. Later ones ease over from what is on display:
 * bars widen or shrink, and a value counts along when both ends are plain numbers in the
 * same unit. The last frame always shows the target text as given.
 */
export function useRankedTableTween(
  targets: () => Map<string, BarTarget>
): Readonly<Ref<Map<string, BarFrame>>> {
  let lastTargets = new Map(targets())
  const shown = new Map<string, Shown>()
  for (const [key, target] of lastTargets) {
    shown.set(key, shownOf(target))
  }
  const frames = shallowRef(framesOf(lastTargets))

  let frame: number | null = null
  let legs = new Map<string, Leg>()
  let startedAt = 0

  function framesOf(settled: Map<string, BarTarget>): Map<string, BarFrame> {
    const result = new Map<string, BarFrame>()
    for (const [key, target] of settled) {
      result.set(key, { percent: target.percent, text: target.text })
    }
    return result
  }

  function cancel(): void {
    if (frame !== null) {
      cancelAnimationFrame(frame)
      frame = null
    }
  }

  function settle(settled: Map<string, BarTarget>): void {
    cancel()
    shown.clear()
    for (const [key, target] of settled) {
      shown.set(key, shownOf(target))
    }
    frames.value = framesOf(settled)
  }

  function step(now: number): void {
    // A frame may carry a timestamp from just before the tween started.
    const progress = Math.min(1, Math.max(0, (now - startedAt) / DURATION_MS))
    const eased = ease(progress)
    const done = progress >= 1
    const next = new Map<string, BarFrame>()
    for (const [key, leg] of legs) {
      const current = frameAt(leg, eased, done)
      next.set(key, current)
      shown.set(
        key,
        leg.counts && !done
          ? {
              percent: current.percent,
              count: countAt(leg, eased),
              decimals: leg.decimals,
              unit: leg.to.unit
            }
          : { ...shownOf(leg.to), percent: current.percent }
      )
    }
    frames.value = next
    frame = done ? null : requestAnimationFrame(step)
  }

  watch(targets, (next) => {
    const unchanged = sameTargets(next, lastTargets)
    lastTargets = new Map(next)
    if (unchanged) {
      return
    }
    if (prefersReducedMotion()) {
      settle(next)
      return
    }

    legs = new Map()
    for (const [key, target] of next) {
      const from = shown.get(key) ?? shownOf(target)
      const counts =
        from.count !== undefined && from.unit === target.unit && PLAIN_NUMBER.test(target.text)
      legs.set(key, {
        from,
        to: target,
        counts,
        decimals: Math.max(from.decimals, decimals(target.text))
      })
    }
    for (const key of shown.keys()) {
      if (!next.has(key)) {
        shown.delete(key)
      }
    }

    cancel()
    startedAt = performance.now()
    step(startedAt)
  })

  onUnmounted(cancel)

  return frames
}
