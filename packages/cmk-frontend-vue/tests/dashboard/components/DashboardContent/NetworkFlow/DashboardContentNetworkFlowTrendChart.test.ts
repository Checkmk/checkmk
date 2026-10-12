/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { waitFor } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'

import DashboardContentNetworkFlowTrendChart from '@/dashboard/components/DashboardContent/NetworkFlow/DashboardContentNetworkFlowTrendChart.vue'
import type {
  ComputedNetworkFlowTrendChart,
  NetworkFlowTrendChartContent
} from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: { template: '<div />' }
}))

const CONTENT: NetworkFlowTrendChartContent = {
  type: 'network_flow_trend_chart',
  dimension: 'applications',
  display_mode: 'stacked_area',
  limit_to: 6,
  show_legend: false
}

const endpoint = useComputeWidgetEndpoint<ComputedNetworkFlowTrendChart>(
  'compute-network-flow-trend-chart',
  () => ({ series: [], time_range: { start: 0, end: 3_600, step: 60 } })
)

describe('DashboardContentNetworkFlowTrendChart', () => {
  it('requests the explicit widget', async () => {
    await renderComputedWidget(DashboardContentNetworkFlowTrendChart, makeContentProps(CONTENT))

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })
})
