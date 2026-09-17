/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkAlertBoxDeprecated from 'cmk-ui-library/components/CmkAlertBoxDeprecated.vue'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

test('CmkAlertBoxDeprecated auto-dismisses after 6s when autoDismiss is true from mount', async () => {
  render(CmkAlertBoxDeprecated, { props: { autoDismiss: true, open: true } })
  screen.getByRole('status')
  await vi.advanceTimersByTimeAsync(6000)
  expect(screen.queryByRole('status')).toBeNull()
})

test('CmkAlertBoxDeprecated auto-dismisses after 6s when autoDismiss is toggled on while already open', async () => {
  const { rerender } = render(CmkAlertBoxDeprecated, { props: { autoDismiss: false, open: true } })
  screen.getByRole('status')
  await rerender({ autoDismiss: true, open: true })
  await vi.advanceTimersByTimeAsync(6000)
  expect(screen.queryByRole('status')).toBeNull()
})

test('CmkAlertBoxDeprecated does not dismiss when autoDismiss is false', async () => {
  render(CmkAlertBoxDeprecated, { props: { autoDismiss: false, open: true } })
  screen.getByRole('status')
  await vi.advanceTimersByTimeAsync(10000)
  screen.getByRole('status')
})

test('CmkAlertBoxDeprecated is named by its heading', () => {
  render(CmkAlertBoxDeprecated, { props: { variant: 'warning', heading: 'Something went wrong' } })
  screen.getByRole('alert', { name: 'Something went wrong' })
})

test('CmkAlertBoxDeprecated without a heading has no accessible name', () => {
  render(CmkAlertBoxDeprecated, { props: { variant: 'warning' } })
  expect(screen.getByRole('alert')).not.toHaveAttribute('aria-labelledby')
})
