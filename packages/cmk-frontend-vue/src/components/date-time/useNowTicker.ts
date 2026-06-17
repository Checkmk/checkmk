/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onScopeDispose, shallowRef, watch } from 'vue'

/**
 * A `Date` ref that re-reads the wall clock at each minute boundary while `active`, then stops and
 * cleans up. It self-reschedules to the next minute (a beat late, never early) rather than polling
 * every second, recomputing the delay on each tick so it stays aligned across drift / DST shifts.
 * Intended for minute-granular readouts (e.g. a "current time" badge) that need not be precise to
 * the second.
 */
export function useNowTicker(active: Ref<boolean>): Ref<Date> {
  const now = shallowRef(new Date())
  let handle: ReturnType<typeof setTimeout> | undefined

  function tick(): void {
    now.value = new Date()
    const msToNextMinute = 60_000 - (now.value.getTime() % 60_000)
    // +50ms so we land just past the boundary rather than a hair before it.
    handle = setTimeout(tick, msToNextMinute + 50)
  }

  watch(
    active,
    (isActive) => {
      clearTimeout(handle)
      handle = undefined
      if (isActive) {
        tick()
      }
    },
    { immediate: true }
  )

  onScopeDispose(() => clearTimeout(handle))

  return now
}
