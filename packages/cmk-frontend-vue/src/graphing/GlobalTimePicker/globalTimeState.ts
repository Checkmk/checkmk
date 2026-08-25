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

let initialised = false
let timerId: ReturnType<typeof setInterval> | null = null

const activeTimeRangeState = computed(() => rangeState.value)
const activeTimeRange = computed(() => rangeState.value.range)

const refreshIntervalSeconds = computed(() => intervalSecondsState.value)
const refreshPaused = computed(() => pausedState.value)
const refreshTick = computed(() => tickState.value)

function setActiveTimeRange(value: ActiveTimeRange, origin: TimeRangeOrigin): void {
  rangeState.value = { range: value, origin }
  // Such a window cannot gain new data. One-way: resuming stays the user's call.
  if (value !== null && endsInThePast(value)) {
    pauseRefresh()
  }
}

function fireRefresh(): void {
  tickState.value += 1
}

function stopTimer(): void {
  if (timerId !== null) {
    clearInterval(timerId)
    timerId = null
  }
}

function restartTimer(): void {
  stopTimer()
  if (pausedState.value) {
    return
  }
  timerId = setInterval(fireRefresh, intervalSecondsState.value * 1000)
}

watch([intervalSecondsState, pausedState], restartTimer, { flush: 'sync' })

function setRefreshIntervalSeconds(seconds: number): void {
  intervalSecondsState.value = seconds
}

function pauseRefresh(): void {
  pausedState.value = true
}

function resumeRefresh(): void {
  // Unpaused first, so the interval that follows is measured from this refresh.
  pausedState.value = false
  fireRefresh()
}

export interface GlobalRefreshInit {
  /** `null` keeps the default. */
  intervalSeconds: number | null
  live: boolean
}

/** Wire the page's refresh, once - a late-mounting host must not clobber what the user picked in
 * the meantime. Never refreshes: what the server just rendered is already that fresh.
 */
export function initGlobalRefresh({ intervalSeconds, live }: GlobalRefreshInit): void {
  if (initialised) {
    return
  }
  initialised = true
  // Defensive: the props carrying the interval are untrusted.
  if (intervalSeconds !== null && Number.isFinite(intervalSeconds) && intervalSeconds > 0) {
    intervalSecondsState.value = intervalSeconds
  }
  pausedState.value = !live
}

/** Only tests need this: a page load starts from a fresh module. */
export function resetGlobalTimeState(): void {
  initialised = false
  tickState.value = 0
  intervalSecondsState.value = DEFAULT_INTERVAL_SECONDS
  pausedState.value = true
  rangeState.value = { range: null, origin: 'time_picker' }
  stopTimer()
}

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
  pauseRefresh: () => void
  /** Goes live and refreshes now: live data means now, not one interval from now. */
  resumeRefresh: () => void
}

export function useGlobalRefresh(): GlobalRefresh {
  return {
    refreshIntervalSeconds,
    refreshPaused,
    refreshTick,
    setRefreshIntervalSeconds,
    pauseRefresh,
    resumeRefresh
  }
}
