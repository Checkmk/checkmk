/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import TimeRangeSource from '@/dashboard/components/TimeRange/TimeRangeSource.vue'
import {
  type TimeRangeSourceModel,
  useTimeRangeSource
} from '@/dashboard/components/TimeRange/useTimeRangeSource'

useMswServer(
  http.get('*/domain-types/graph_timerange/collections/all', () => HttpResponse.json({ value: [] }))
)

function renderSource(current: TimeRangeSourceModel | null) {
  const source = useTimeRangeSource(current)
  const wrapper = defineComponent({
    setup() {
      return () =>
        h(TimeRangeSource, {
          followDashboard: source.followDashboard.value,
          'onUpdate:followDashboard': (value: boolean) => (source.followDashboard.value = value),
          selectedTimerange: source.timeRange.value,
          'onUpdate:selectedTimerange': (value: typeof source.timeRange.value) =>
            (source.timeRange.value = value)
        })
    }
  })
  render(wrapper)
  return source
}

describe('TimeRangeSource', () => {
  it('selects the dashboard time range for a new widget', () => {
    renderSource(null)

    expect(screen.getByRole('radio', { name: 'Follow dashboard time range' })).toBeChecked()
    expect(screen.queryByRole('combobox')).toBeNull()
  })

  it('selects the separate time range for a stored range', () => {
    renderSource({ type: 'graph', duration: 3600 })

    expect(screen.getByRole('radio', { name: 'Use separate time range' })).toBeChecked()
  })

  it('offers the time range input once the separate time range is selected', async () => {
    const source = renderSource(null)

    await userEvent.click(screen.getByRole('radio', { name: 'Use separate time range' }))

    expect(source.widgetProps()).not.toBe('dashboard')
    expect(await screen.findByRole('combobox')).toBeInTheDocument()
  })
})
