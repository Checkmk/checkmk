/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, vi } from 'vitest'

import {
  resetGlobalRefresh,
  seedRefreshIntervalSeconds,
  useGlobalRefresh
} from '@/graphing/GlobalRefreshControl/useGlobalRefresh'

beforeEach(() => {
  vi.useFakeTimers()
  resetGlobalRefresh()
})

afterEach(() => {
  resetGlobalRefresh()
  vi.useRealTimers()
})

test('starts paused with the default interval', () => {
  expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(30)
})

test('a write is visible to a second consumer', () => {
  const writer = useGlobalRefresh()
  const reader = useGlobalRefresh()

  writer.setRefreshIntervalSeconds(60)

  expect(reader.refreshIntervalSeconds.value).toBe(60)
})

test('resuming refreshes immediately, then ticks at the configured interval', () => {
  const { setRefreshPaused, refreshTick } = useGlobalRefresh()
  const ticksBefore = refreshTick.value

  setRefreshPaused(false)
  expect(refreshTick.value).toBe(ticksBefore + 1)

  vi.advanceTimersByTime(30_000)
  expect(refreshTick.value).toBe(ticksBefore + 2)

  vi.advanceTimersByTime(60_000)
  expect(refreshTick.value).toBe(ticksBefore + 4)
})

test('pausing stops the timer and keeps the interval', () => {
  const { setRefreshPaused, refreshIntervalSeconds, refreshTick } = useGlobalRefresh()
  setRefreshPaused(false)
  vi.advanceTimersByTime(30_000)
  const ticksWhenPaused = refreshTick.value

  setRefreshPaused(true)
  vi.advanceTimersByTime(90_000)

  expect(refreshTick.value).toBe(ticksWhenPaused)
  expect(refreshIntervalSeconds.value).toBe(30)
})

test('changing the interval restarts the timer without an immediate refresh', () => {
  const { setRefreshIntervalSeconds, setRefreshPaused, refreshTick } = useGlobalRefresh()
  setRefreshPaused(false)
  vi.advanceTimersByTime(20_000)
  const ticksBefore = refreshTick.value

  setRefreshIntervalSeconds(60)
  expect(refreshTick.value).toBe(ticksBefore)

  vi.advanceTimersByTime(30_000)
  expect(refreshTick.value).toBe(ticksBefore)
  vi.advanceTimersByTime(30_000)
  expect(refreshTick.value).toBe(ticksBefore + 1)
})

test('changing the interval while paused does not start the timer', () => {
  const { setRefreshIntervalSeconds, refreshTick } = useGlobalRefresh()
  const ticksBefore = refreshTick.value

  setRefreshIntervalSeconds(60)
  vi.advanceTimersByTime(120_000)

  expect(refreshTick.value).toBe(ticksBefore)
})

test('seeding a preferred interval preselects it without starting the timer', () => {
  const { refreshIntervalSeconds, refreshPaused, refreshTick } = useGlobalRefresh()
  const ticksBefore = refreshTick.value

  seedRefreshIntervalSeconds(60)
  vi.advanceTimersByTime(120_000)

  expect(refreshIntervalSeconds.value).toBe(60)
  expect(refreshPaused.value).toBe(true)
  expect(refreshTick.value).toBe(ticksBefore)
})

test('seeding null keeps the default interval', () => {
  seedRefreshIntervalSeconds(null)
  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(30)
})

test('only the first seed wins', () => {
  seedRefreshIntervalSeconds(60)
  seedRefreshIntervalSeconds(90)
  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(60)
})

test('a bogus value does not consume the one-shot', () => {
  seedRefreshIntervalSeconds(Number.NaN)
  seedRefreshIntervalSeconds(60)

  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(60)
})
