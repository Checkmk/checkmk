/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'

import GlobalRefreshControl from '@/graphing/GlobalRefreshControl/GlobalRefreshControl.vue'
import {
  initGlobalTime,
  resetGlobalTimeState,
  useGlobalRefresh
} from '@/graphing/GlobalTimePicker/globalTimeState'

const PROPS = { lastRefreshPosition: 'top' as const, intervalChoicesSeconds: [30, 60, 90] }

beforeEach(() => {
  resetGlobalTimeState()
})

afterEach(() => {
  resetGlobalTimeState()
  vi.useRealTimers()
})

test('starts in the paused state showing "Refresh off" and Resume', () => {
  render(GlobalRefreshControl, { props: PROPS })

  expect(screen.getByText('Refresh off')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Resume live refresh' })).toBeInTheDocument()
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
})

test('live state shows the badge and the interval dropdown', async () => {
  useGlobalRefresh().resumeRefresh()

  render(GlobalRefreshControl, { props: PROPS })

  expect(screen.getByText('Live refresh')).toBeInTheDocument()
  const intervalDropdown = screen.getByRole('combobox', { name: 'Live refresh every' })
  await waitFor(() => expect(intervalDropdown).toHaveTextContent('30 sec'))
  expect(screen.queryByText('Refresh off')).not.toBeInTheDocument()
})

test('selecting another interval stores it unpaused', async () => {
  const user = userEvent.setup()
  useGlobalRefresh().resumeRefresh()
  render(GlobalRefreshControl, { props: PROPS })

  await user.click(screen.getByRole('combobox', { name: 'Live refresh every' }))
  await user.click(await screen.findByText('60 sec'))

  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(60)
  expect(useGlobalRefresh().refreshPaused.value).toBe(false)
})

test('selecting another interval announces it', async () => {
  const user = userEvent.setup()
  useGlobalRefresh().resumeRefresh()
  render(GlobalRefreshControl, { props: PROPS })

  await user.click(screen.getByRole('combobox', { name: 'Live refresh every' }))
  await user.click(await screen.findByText('60 sec'))

  await waitFor(() =>
    expect(screen.getByRole('status')).toHaveTextContent('Refresh interval set to 60 seconds')
  )
})

test('"Turn off" pauses and keeps the interval', async () => {
  const user = userEvent.setup()
  useGlobalRefresh().resumeRefresh()
  render(GlobalRefreshControl, { props: PROPS })

  await user.click(screen.getByRole('combobox', { name: 'Live refresh every' }))
  await user.click(await screen.findByText('Turn off'))

  expect(useGlobalRefresh().refreshPaused.value).toBe(true)
  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(30)
})

test('"Turn off" announces that the live refresh is off', async () => {
  const user = userEvent.setup()
  useGlobalRefresh().resumeRefresh()
  render(GlobalRefreshControl, { props: PROPS })

  await user.click(screen.getByRole('combobox', { name: 'Live refresh every' }))
  await user.click(await screen.findByText('Turn off'))

  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Live refresh off'))
})

test('paused state shows the time of the last refresh tick', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date(2026, 6, 9, 10, 33, 49))
  render(GlobalRefreshControl, { props: PROPS })
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
  render(GlobalRefreshControl, { props: PROPS })
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
  render(GlobalRefreshControl, { props: PROPS })

  expect(screen.queryByText(/Last refresh/)).not.toBeInTheDocument()
})

test('picking an interval changes the rhythm, not the data on screen', async () => {
  const user = userEvent.setup()
  useGlobalRefresh().resumeRefresh()
  render(GlobalRefreshControl, { props: PROPS })
  const ticksBefore = useGlobalRefresh().refreshTick.value

  await user.click(screen.getByRole('combobox', { name: 'Live refresh every' }))
  await user.click(await screen.findByText('60 sec'))

  expect(useGlobalRefresh().refreshTick.value).toBe(ticksBefore)
})

test('offers the intervals it is given, next to the current one', async () => {
  const user = userEvent.setup()
  useGlobalRefresh().resumeRefresh()
  render(GlobalRefreshControl, { props: { ...PROPS, intervalChoicesSeconds: [60, 120] } })

  await user.click(screen.getByRole('combobox', { name: 'Live refresh every' }))

  await screen.findByText('120 sec')
  expect(screen.getAllByRole('option').map((option) => option.textContent?.trim())).toEqual([
    '30 sec',
    '60 sec',
    '120 sec',
    'Turn off'
  ])
})

test('Resume goes live, keeping the interval that was chosen before', async () => {
  const chosenInterval = useGlobalRefresh().refreshIntervalSeconds.value
  render(GlobalRefreshControl, { props: PROPS })

  await fireEvent.click(screen.getByRole('button', { name: /Resume/ }))

  expect(useGlobalRefresh().refreshPaused.value).toBe(false)
  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(chosenInterval)
})

test('Resume announces that the live refresh resumed, with its interval', async () => {
  useGlobalRefresh().setRefreshIntervalSeconds(60)
  useGlobalRefresh().pauseRefresh()
  render(GlobalRefreshControl, { props: PROPS })

  await fireEvent.click(screen.getByRole('button', { name: 'Resume live refresh' }))

  await waitFor(() =>
    expect(screen.getByRole('status')).toHaveTextContent('Live refresh resumed, every 60 seconds')
  )
})

describe('the interval picked is the one the clock runs on', () => {
  // As the backend hands them over: the intervals offered, and the current one among them.
  const BACKEND_INTERVALS_SECONDS = [1, 2, 3]

  function renderLive(): ReturnType<typeof userEvent.setup> {
    vi.useFakeTimers()
    initGlobalTime({
      intervalSeconds: BACKEND_INTERVALS_SECONDS[0]!,
      start: { type: 'page_default', live: true }
    })
    render(GlobalRefreshControl, {
      props: { ...PROPS, intervalChoicesSeconds: BACKEND_INTERVALS_SECONDS }
    })
    return userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
  }

  async function pick(user: ReturnType<typeof userEvent.setup>, option: string): Promise<void> {
    await user.click(screen.getByRole('combobox', { name: 'Live refresh every' }))
    await user.click(await screen.findByRole('option', { name: option }))
  }

  test('offers the intervals the backend sends, and turning the refresh off', async () => {
    const user = renderLive()

    await user.click(screen.getByRole('combobox', { name: 'Live refresh every' }))

    await screen.findByText('3 sec')
    expect(screen.getAllByRole('option').map((option) => option.textContent?.trim())).toEqual([
      '1 sec',
      '2 sec',
      '3 sec',
      'Turn off'
    ])
  })

  test.each([{ seconds: 1 }, { seconds: 2 }, { seconds: 3 }])(
    'picking $seconds sec refreshes once every $seconds seconds, not before',
    async ({ seconds }) => {
      const user = renderLive()
      await pick(user, `${seconds} sec`)
      const ticksBefore = useGlobalRefresh().refreshTick.value

      vi.advanceTimersByTime(seconds * 1000 - 1)
      const ticksJustBefore = useGlobalRefresh().refreshTick.value
      vi.advanceTimersByTime(1)

      expect(ticksJustBefore).toBe(ticksBefore)
      expect(useGlobalRefresh().refreshTick.value).toBe(ticksBefore + 1)
    }
  )

  test('"Turn off" stops the clock', async () => {
    const user = renderLive()
    await pick(user, 'Turn off')
    const ticksBefore = useGlobalRefresh().refreshTick.value

    vi.advanceTimersByTime(10 * Math.max(...BACKEND_INTERVALS_SECONDS) * 1000)

    expect(useGlobalRefresh().refreshTick.value).toBe(ticksBefore)
  })
})
