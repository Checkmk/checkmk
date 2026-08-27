/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { formatOverviewExtent } from '@/graphing/components/GraphBrush/utils'
import type { TimeRange } from '@/graphing/components/TimeSeriesGraph'

describe('formatOverviewExtent', () => {
  test('a multi-day extent shows the start and end dates', () => {
    const domain: TimeRange = { start: 1_700_000_000, end: 1_700_000_000 + 5 * 86_400, step: 60 }

    const label = formatOverviewExtent(domain, 'UTC')

    expect(label).toBe('2023-11-14 — 2023-11-19')
  })

  test('a same-day extent shows the date once with a start–end time range', () => {
    const start = 1_700_000_000
    const domain: TimeRange = { start, end: start + 3600, step: 60 }

    const label = formatOverviewExtent(domain, 'UTC')

    expect(label).toBe('2023-11-14 22:13–23:13')
  })
})
