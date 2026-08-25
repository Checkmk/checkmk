/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { type ComputedRef, computed, ref, shallowRef, watch } from 'vue'

import { endsInThePast } from './private/timeRange'

export type TimeRangeOrigin = 'time_picker' | 'external'

export type ActiveTimeRange = DateTimeRange | null

export interface ActiveTimeRangeState {
  range: ActiveTimeRange
  origin: TimeRangeOrigin
}

const DEFAULT_INTERVAL_SECONDS = 30

// Shared across the page's separate Vue apps. The range is a shallow ref: replace the value,
// never mutate it.
const rangeState = shallowRef<ActiveTimeRangeState>({ range: null, origin: 'time_picker' })
const intervalSecondsState = ref(DEFAULT_INTERVAL_SECONDS)
const pausedState = ref(true)
const tickState = ref(0)

const activeTimeRangeState = computed(() => rangeState.value)
const activeTimeRange = computed(() => rangeState.value.range)

const refreshIntervalSeconds = computed(() => intervalSecondsState.value)
const refreshPaused = computed(() => pausedState.value)
const refreshTick = computed(() => tickState.value)

function setActiveTimeRange(value: ActiveTimeRange, origin: TimeRangeOrigin): void {
  rangeState.value = { range: value, origin }
  // Such a window cannot gain new data. One-way: resuming stays the user's call.
  if (value !== null && endsInThePast(value)) {
    setRefreshPaused(true)
  }
}

function setRefreshIntervalSeconds(seconds: number): void {
  intervalSecondsState.value = seconds
}

function setRefreshPaused(paused: boolean): void {
  pausedState.value = paused
}

let seededFromPreference = false

/** Seed the interval from the user's profile preference, once per page load - a late-mounting host
 * must not clobber a choice the user made in the meantime. `null` = no preference. Only
 * preselects: never unpauses.
 */
export function seedRefreshIntervalSeconds(defaultRefreshTime: number | null): void {
  if (seededFromPreference || defaultRefreshTime === null) {
    return
  }
  // Defensive: the props carrying the interval are untrusted.
  if (!Number.isFinite(defaultRefreshTime) || defaultRefreshTime <= 0) {
    return
  }
  // Consumed only once a seed takes effect, so a bogus value cannot swallow a later one.
  seededFromPreference = true
  intervalSecondsState.value = defaultRefreshTime
}

/** Only tests need this: a page load starts from a fresh module. */
export function resetGlobalTimeState(): void {
  seededFromPreference = false
  intervalSecondsState.value = DEFAULT_INTERVAL_SECONDS
  pausedState.value = true
  rangeState.value = { range: null, origin: 'time_picker' }
}

function fireRefresh(): void {
  tickState.value += 1
}

let timerId: ReturnType<typeof setInterval> | null = null

watch(
  [intervalSecondsState, pausedState],
  ([intervalSeconds, paused], [, previouslyPaused]) => {
    if (timerId !== null) {
      clearInterval(timerId)
      timerId = null
    }
    if (paused) {
      return
    }
    if (previouslyPaused) {
      fireRefresh()
    }
    timerId = setInterval(fireRefresh, intervalSeconds * 1000)
  },
  { flush: 'sync' }
)

export interface GlobalTimeRange {
  activeTimeRange: ComputedRef<ActiveTimeRange>
  activeTimeRangeState: ComputedRef<ActiveTimeRangeState>
  setActiveTimeRange: (value: ActiveTimeRange, origin: TimeRangeOrigin) => void
}

export function useGlobalTimeRange(): GlobalTimeRange {
  return { activeTimeRange, activeTimeRangeState, setActiveTimeRange }
}

export interface GlobalRefresh {
  refreshIntervalSeconds: ComputedRef<number>
  refreshPaused: ComputedRef<boolean>
  refreshTick: ComputedRef<number>
  setRefreshIntervalSeconds: (seconds: number) => void
  setRefreshPaused: (paused: boolean) => void
}

export function useGlobalRefresh(): GlobalRefresh {
  return {
    refreshIntervalSeconds,
    refreshPaused,
    refreshTick,
    setRefreshIntervalSeconds,
    setRefreshPaused
  }
}
