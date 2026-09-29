/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useTimeRangeSource } from '@/dashboard/components/TimeRange/useTimeRangeSource'

describe('useTimeRangeSource', () => {
  it('follows the dashboard for a new widget', () => {
    const { followDashboard, widgetProps } = useTimeRangeSource(null)

    expect(followDashboard.value).toBe(true)
    expect(widgetProps()).toBe('dashboard')
  })

  it('opens a stored range as the separate time range', () => {
    const { followDashboard, widgetProps } = useTimeRangeSource({ type: 'graph', duration: 3600 })

    expect(followDashboard.value).toBe(false)
    expect(widgetProps()).toEqual({ type: 'graph', duration: 3600 })
  })

  it('keeps the separate time range across a switch to the dashboard and back', () => {
    const { followDashboard, widgetProps } = useTimeRangeSource({ type: 'graph', duration: 3600 })

    followDashboard.value = true
    followDashboard.value = false

    expect(widgetProps()).toEqual({ type: 'graph', duration: 3600 })
  })
})
