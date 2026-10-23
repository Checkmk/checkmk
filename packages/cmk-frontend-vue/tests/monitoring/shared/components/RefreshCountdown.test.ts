/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import RefreshCountdown from '@/monitoring/shared/components/RefreshCountdown.vue'

test('offers to pause the reload countdown while it runs', () => {
  render(RefreshCountdown, { props: { remaining: 12, interval: 30 } })

  expect(screen.getByRole('button')).toHaveAttribute('title', 'Pause reload countdown')
})

test('offers to continue the reload countdown once the user paused it', () => {
  render(RefreshCountdown, {
    props: { remaining: 12, interval: 30, paused: true, manualPaused: true }
  })

  expect(screen.getByRole('button')).toHaveAttribute('title', 'Continue reload countdown')
})

test('still offers to pause the reload countdown while the page holds it on its own', () => {
  render(RefreshCountdown, { props: { remaining: 12, interval: 30, paused: true } })

  expect(screen.getByRole('button')).toHaveAttribute('title', 'Pause reload countdown')
})

test('names the button for a screen reader in the words of its tooltip', () => {
  render(RefreshCountdown, { props: { remaining: 12, interval: 30 } })

  expect(
    screen.getByRole('button', { name: 'Pause reload countdown, next reload in 12 seconds' })
  ).toBeInTheDocument()
})
