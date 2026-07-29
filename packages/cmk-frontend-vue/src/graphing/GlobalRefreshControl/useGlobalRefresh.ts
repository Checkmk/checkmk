/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed, ref, watch } from 'vue'

const DEFAULT_INTERVAL_SECONDS = 30

const intervalSecondsState = ref(DEFAULT_INTERVAL_SECONDS)
const pausedState = ref(true)
const tickState = ref(0)

const refreshIntervalSeconds = computed(() => intervalSecondsState.value)
const refreshPaused = computed(() => pausedState.value)
const refreshTick = computed(() => tickState.value)

function setRefreshIntervalSeconds(seconds: number): void {
  intervalSecondsState.value = seconds
}

function setRefreshPaused(paused: boolean): void {
  pausedState.value = paused
}

let seededFromPreference = false

/** Seed the interval from the user's profile preference, once per page load (a one-shot so a
 * late-mounting host cannot clobber choices the user made in the meantime). `null` = no
 * preference, in which case the default stands. Only preselects: never unpauses.
 */
export function seedRefreshIntervalSeconds(defaultRefreshTime: number | null): void {
  if (seededFromPreference || defaultRefreshTime === null) {
    return
  }
  // Defensive: the profile setting only offers the intervals below, but the props are untrusted.
  if (!Number.isFinite(defaultRefreshTime) || defaultRefreshTime <= 0) {
    return
  }
  // Consumed only once a seed takes effect, so a bogus value cannot swallow a later one.
  seededFromPreference = true
  intervalSecondsState.value = defaultRefreshTime
}

/** Only tests need this: a page load starts from a fresh module, and the seeding one-shot is
 * not reachable through the public setters.
 */
export function resetGlobalRefresh(): void {
  seededFromPreference = false
  pausedState.value = true
  intervalSecondsState.value = DEFAULT_INTERVAL_SECONDS
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
