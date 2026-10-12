/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentNetworkFlowKpiStatCard from '@/dashboard/components/DashboardContent/NetworkFlow/DashboardContentNetworkFlowKpiStatCard.vue'
import type {
  ComputedNetworkFlowKpiStatCard,
  NetworkFlowKpiStatCardContent
} from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const CONTENT: NetworkFlowKpiStatCardContent = {
  type: 'network_flow_kpi_stat_card',
  metric: 'total_flows',
  accent: 'blue',
  show_delta: false,
  spark_height_mode: 'band'
}

const endpoint = useComputeWidgetEndpoint<ComputedNetworkFlowKpiStatCard>(
  'compute-network-flow-kpi-stat-card',
  () => ({ value: 532, previous_value: 0, series: [] })
)

describe('DashboardContentNetworkFlowKpiStatCard', () => {
  it('requests the explicit widget', async () => {
    await renderComputedWidget(DashboardContentNetworkFlowKpiStatCard, makeContentProps(CONTENT))
    await screen.findByText('532')

    expect(endpoint.requests).toEqual([
      { source: { type: 'explicit', content: CONTENT, context: {} } }
    ])
  })
})
