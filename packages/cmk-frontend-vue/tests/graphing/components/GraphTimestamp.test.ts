/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as intl from '@internationalized/date'
import { render, screen } from '@testing-library/vue'

import GraphTimestamp from '@/graphing/components/GraphTimestamp.vue'

vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, getLocalTimeZone: () => 'UTC' }
})

// 2026-06-15 12:00:00 UTC (Monday)
const JUNE_15_NOON = 1781524800
// 2026-06-14 12:00:00 UTC (Sunday)
const JUNE_14_NOON = JUNE_15_NOON - 86400

test('same-day range: shows weekday, ISO date, and step', () => {
  render(GraphTimestamp, {
    props: { timeRange: { start: JUNE_15_NOON, end: JUNE_15_NOON + 3600, step: 300 } }
  })
  expect(screen.getByText(/2026-06-15.*@ 5 m/)).toBeInTheDocument()
})

test('cross-day range: shows start — end and step', () => {
  render(GraphTimestamp, {
    props: { timeRange: { start: JUNE_14_NOON, end: JUNE_15_NOON, step: 300 } }
  })
  expect(screen.getByText(/2026-06-14 — 2026-06-15.*@ 5 m/)).toBeInTheDocument()
})
