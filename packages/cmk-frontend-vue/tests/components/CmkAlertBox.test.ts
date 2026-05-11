/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

test('CmkAlertBox auto-dismisses after 6s when autoDismiss is true from mount', async () => {
  render(CmkAlertBox, { props: { autoDismiss: true, open: true } })
  screen.getByRole('status')
  await vi.advanceTimersByTimeAsync(6000)
  expect(screen.queryByRole('status')).toBeNull()
})

test('CmkAlertBox auto-dismisses after 6s when autoDismiss is toggled on while already open', async () => {
  const { rerender } = render(CmkAlertBox, { props: { autoDismiss: false, open: true } })
  screen.getByRole('status')
  await rerender({ autoDismiss: true, open: true })
  await vi.advanceTimersByTimeAsync(6000)
  expect(screen.queryByRole('status')).toBeNull()
})

test('CmkAlertBox does not dismiss when autoDismiss is false', async () => {
  render(CmkAlertBox, { props: { autoDismiss: false, open: true } })
  screen.getByRole('status')
  await vi.advanceTimersByTimeAsync(10000)
  screen.getByRole('status')
})
