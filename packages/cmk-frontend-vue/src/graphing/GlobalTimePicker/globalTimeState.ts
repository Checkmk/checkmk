/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { type ComputedRef, computed, ref, shallowRef, watch } from 'vue'

import { durationSeconds, endsInThePast, isRolling, rollingRange } from './private/timeRange'

export type TimeRangeOrigin = 'time_picker' | 'external'

export type ActiveTimeRange = DateTimeRange | null

export interface ActiveTimeRangeState {
  range: ActiveTimeRange
  origin: TimeRangeOrigin
}

/** What a refresh does beyond publishing a tick. `onContentReady` is expected on every path the
 * strategy can take: it releases the fetch owners the coming content swap unmounts, see
 * `GlobalRefresh.contentReloadPending`.
 */
export type RefreshStrategy = (onContentReady: () => void) => void

const DEFAULT_INTERVAL_SECONDS = 30

// Shared across the page's separate Vue apps. The range is a shallow ref: replace the value,
// never mutate it.
const rangeState = shallowRef<ActiveTimeRangeState>({ range: null, origin: 'time_picker' })
const intervalSecondsState = ref(DEFAULT_INTERVAL_SECONDS)
const pausedState = ref(true)
const tickState = ref(0)

let initialised = false
let strategy: RefreshStrategy | null = null
let timerId: ReturnType<typeof setInterval> | null = null
let lastRefreshAtMs: number | null = null

let contentReloadInFlight = false
// Identifies the reload, so one reporting back late cannot release a later tick's suppression.
let contentReloads = 0

const activeTimeRangeState = computed(() => rangeState.value)
const activeTimeRange = computed(() => rangeState.value.range)

const refreshIntervalSeconds = computed(() => intervalSecondsState.value)
const refreshPaused = computed(() => pausedState.value)
const refreshTick = computed(() => tickState.value)

function setRange(value: ActiveTimeRange, origin: TimeRangeOrigin): void {
  rangeState.value = { range: value, origin }
}

function setActiveTimeRange(value: ActiveTimeRange, origin: TimeRangeOrigin): void {
  setRange(value, origin)
  // Such a window cannot gain new data. One-way: resuming stays the user's call.
  if (value !== null && endsInThePast(value)) {
    pauseRefresh()
  }
}

/** Through `setRange`, not `setActiveTimeRange`: the clock catching up is not a user's pick. */
function advanceRollingWindow(): void {
  const current = rangeState.value.range
  if (current === null || !isRolling(current)) {
    return
  }
  setRange(rollingRange(durationSeconds(current)), 'time_picker')
}

function fireRefresh(): void {
  const reload = ++contentReloads
  // Armed before the tick, so every fetch owner the coming swap unmounts sees it.
  contentReloadInFlight = strategy !== null
  lastRefreshAtMs = Date.now()
  advanceRollingWindow()
  tickState.value += 1
  strategy?.(() => {
    if (reload === contentReloads) {
      contentReloadInFlight = false
    }
  })
}

function stopTimer(): void {
  if (timerId !== null) {
    clearInterval(timerId)
    timerId = null
  }
}

function restartTimer(): void {
  stopTimer()
  if (pausedState.value || document.hidden) {
    return
  }
  timerId = setInterval(fireRefresh, intervalSecondsState.value * 1000)
}

watch([intervalSecondsState, pausedState], restartTimer, { flush: 'sync' })

// A hidden tab has nobody to show fresh data to, so the clock stops rather than piling up fetches.
function onVisibilityChange(): void {
  const missedARefresh =
    lastRefreshAtMs === null || Date.now() - lastRefreshAtMs >= intervalSecondsState.value * 1000
  if (!document.hidden && !pausedState.value && missedARefresh) {
    fireRefresh()
  }
  restartTimer()
}

document.addEventListener('visibilitychange', onVisibilityChange)

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
  strategy?: RefreshStrategy
}

/** Wire the page's refresh, once - a late-mounting host must not clobber what the user picked in
 * the meantime. Never refreshes: what the server just rendered is already that fresh.
 */
export function initGlobalRefresh({
  intervalSeconds,
  live,
  strategy: refresh
}: GlobalRefreshInit): void {
  if (initialised) {
    return
  }
  initialised = true
  strategy = refresh ?? null
  // Defensive: the props carrying the interval are untrusted.
  if (intervalSeconds !== null && Number.isFinite(intervalSeconds) && intervalSeconds > 0) {
    intervalSecondsState.value = intervalSeconds
  }
  pausedState.value = !live
  // The interval runs from what the server just rendered, so coming back to the tab inside it is
  // not a missed refresh.
  lastRefreshAtMs = Date.now()
}

/** Only tests need this: a page load starts from a fresh module. */
export function resetGlobalTimeState(): void {
  initialised = false
  strategy = null
  contentReloadInFlight = false
  contentReloads = 0
  lastRefreshAtMs = null
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
  /** Whether a content reload is between asked for and swapped in: a fetch owner about to be
   * unmounted skips instead. A function, not a ref: a reactive read would re-run the watcher
   * that skipped a fetch, issuing it on release.
   */
  contentReloadPending: () => boolean
}

export function useGlobalRefresh(): GlobalRefresh {
  return {
    refreshIntervalSeconds,
    refreshPaused,
    refreshTick,
    setRefreshIntervalSeconds,
    pauseRefresh,
    resumeRefresh,
    contentReloadPending: () => contentReloadInFlight
  }
}
