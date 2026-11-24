/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, expect, test, vi } from 'vitest'

import WidgetDataErrorAlert from '@/dashboard/components/DashboardContent/figures/WidgetDataErrorAlert.vue'

afterEach(() => {
  vi.useRealTimers()
})

test('gives the server detail when no fetch has succeeded yet', () => {
  render(WidgetDataErrorAlert, { props: { detail: 'Livestatus unavailable' } })

  expect(screen.getByRole('alert')).toHaveTextContent(
    'Data could not be loaded' + 'Livestatus unavailable'
  )
})

test('tells how long ago data last arrived', () => {
  vi.useFakeTimers({ now: 10 * 60_000 })

  render(WidgetDataErrorAlert, { props: { detail: 'down', lastSuccessAt: 3 * 60_000 } })

  expect(screen.getByRole('alert')).toHaveTextContent('Last successful update 7 min ago.')
})

test('tells a success under a minute ago as such', () => {
  vi.useFakeTimers({ now: 10 * 60_000 })

  render(WidgetDataErrorAlert, { props: { detail: 'down', lastSuccessAt: 10 * 60_000 - 20_000 } })

  expect(screen.getByRole('alert')).toHaveTextContent(
    'Last successful update less than a minute ago.'
  )
})

test('keeps the age current while the alert is shown', async () => {
  vi.useFakeTimers({ now: 10 * 60_000 })
  render(WidgetDataErrorAlert, { props: { detail: 'down', lastSuccessAt: 3 * 60_000 } })

  await vi.advanceTimersByTimeAsync(2 * 60_000)

  expect(screen.getByRole('alert')).toHaveTextContent('Last successful update 9 min ago.')
})

test('asks for a retry from its button', async () => {
  const { emitted } = render(WidgetDataErrorAlert, { props: { detail: 'down' } })

  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

  expect(emitted('retry')).toHaveLength(1)
})
