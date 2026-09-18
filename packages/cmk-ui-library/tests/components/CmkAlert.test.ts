/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

test('CmkAlert auto-dismisses after 6s when autoDismiss is true from mount', async () => {
  render(CmkAlert, { props: { autoDismiss: true, open: true } })
  screen.getByRole('status')
  await vi.advanceTimersByTimeAsync(6000)
  expect(screen.queryByRole('status')).toBeNull()
})

test('CmkAlert auto-dismisses after 6s when autoDismiss is toggled on while already open', async () => {
  const { rerender } = render(CmkAlert, { props: { autoDismiss: false, open: true } })
  screen.getByRole('status')
  await rerender({ autoDismiss: true, open: true })
  await vi.advanceTimersByTimeAsync(6000)
  expect(screen.queryByRole('status')).toBeNull()
})

test('CmkAlert does not dismiss when autoDismiss is false', async () => {
  render(CmkAlert, { props: { autoDismiss: false, open: true } })
  screen.getByRole('status')
  await vi.advanceTimersByTimeAsync(10000)
  screen.getByRole('status')
})

test('CmkAlert is named by its heading', () => {
  render(CmkAlert, { props: { variant: 'warning', heading: 'Something went wrong' } })
  screen.getByRole('alert', { name: 'Something went wrong' })
})

test('CmkAlert without a heading has no accessible name', () => {
  render(CmkAlert, { props: { variant: 'warning' } })
  expect(screen.getByRole('alert')).not.toHaveAttribute('aria-labelledby')
})
