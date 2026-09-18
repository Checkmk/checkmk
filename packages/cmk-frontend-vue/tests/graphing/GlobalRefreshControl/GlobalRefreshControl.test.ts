/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'

import GlobalRefreshControl from '@/graphing/GlobalRefreshControl/GlobalRefreshControl.vue'
import { resetGlobalTimeState, useGlobalRefresh } from '@/graphing/GlobalTimePicker/globalTimeState'

beforeEach(() => {
  resetGlobalTimeState()
})

afterEach(() => {
  resetGlobalTimeState()
  vi.useRealTimers()
})

test('starts in the paused state showing "Refresh off" and Resume', () => {
  render(GlobalRefreshControl)

  expect(screen.getByText('Refresh off')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Resume/ })).toBeInTheDocument()
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
})

test('live state shows the badge and the interval dropdown', () => {
  useGlobalRefresh().resumeRefresh()

  render(GlobalRefreshControl)

  expect(screen.getByText('Live refresh')).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Refresh interval' })).toBeInTheDocument()
  expect(screen.queryByText('Refresh off')).not.toBeInTheDocument()
})

test('selecting another interval stores it unpaused', async () => {
  const user = userEvent.setup()
  useGlobalRefresh().resumeRefresh()
  render(GlobalRefreshControl)

  await user.click(screen.getByRole('combobox', { name: 'Refresh interval' }))
  await user.click(await screen.findByText('60 sec'))

  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(60)
  expect(useGlobalRefresh().refreshPaused.value).toBe(false)
})

test('"Turn off" pauses and keeps the interval', async () => {
  const user = userEvent.setup()
  useGlobalRefresh().resumeRefresh()
  render(GlobalRefreshControl)

  await user.click(screen.getByRole('combobox', { name: 'Refresh interval' }))
  await user.click(await screen.findByText('Turn off'))

  expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(30)
})

test('paused state shows the time of the last refresh tick', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date(2026, 6, 9, 10, 33, 49))
  render(GlobalRefreshControl)
  useGlobalRefresh().resumeRefresh()

  vi.advanceTimersByTime(30_000)
  useGlobalRefresh().pauseRefresh()
  await nextTick()
  await nextTick()

  expect(screen.getByText('Last refresh: 10:34:19')).toBeInTheDocument()
})

test('the last refresh time stays put while paused instead of following the clock', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date(2026, 6, 9, 10, 33, 49))
  render(GlobalRefreshControl)
  useGlobalRefresh().resumeRefresh()
  vi.advanceTimersByTime(30_000)
  useGlobalRefresh().pauseRefresh()
  await nextTick()
  await nextTick()
  const timeOfLastRefresh = screen.getByText(/Last refresh/).textContent!

  vi.advanceTimersByTime(10 * 60_000)
  await nextTick()

  expect(screen.getByText(/Last refresh/)).toHaveTextContent(timeOfLastRefresh)
})

test('the last refresh time is omitted when never refreshed', () => {
  render(GlobalRefreshControl)

  expect(screen.queryByText(/Last refresh/)).not.toBeInTheDocument()
})

test('picking an interval changes the rhythm, not the data on screen', async () => {
  const user = userEvent.setup()
  useGlobalRefresh().resumeRefresh()
  render(GlobalRefreshControl)
  const ticksBefore = useGlobalRefresh().refreshTick.value

  await user.click(screen.getByRole('combobox', { name: 'Refresh interval' }))
  await user.click(await screen.findByText('60 sec'))

  expect(useGlobalRefresh().refreshTick.value).toBe(ticksBefore)
})

test('Resume goes live, keeping the interval that was chosen before', async () => {
  const chosenInterval = useGlobalRefresh().refreshIntervalSeconds.value
  render(GlobalRefreshControl)

  await fireEvent.click(screen.getByRole('button', { name: /Resume/ }))

  expect(useGlobalRefresh().refreshPaused.value).toBe(false)
  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(chosenInterval)
})
