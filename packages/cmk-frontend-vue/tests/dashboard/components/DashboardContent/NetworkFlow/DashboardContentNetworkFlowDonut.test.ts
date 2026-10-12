/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentNetworkFlowDonut from '@/dashboard/components/DashboardContent/NetworkFlow/DashboardContentNetworkFlowDonut.vue'
import type { ComputedNetworkFlowDonut, NetworkFlowDonutContent } from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const CONTENT: NetworkFlowDonutContent = {
  type: 'network_flow_donut',
  dimension: 'applications',
  limit_to: 6,
  legend_mode: 'table',
  show_delta: false
}

const endpoint = useComputeWidgetEndpoint<ComputedNetworkFlowDonut>(
  'compute-network-flow-donut',
  () => ({
    slices: [{ label: 'HTTPS', value: 1_000 }],
    total: 1_000,
    window_from: 0,
    window_until: 3_600
  })
)

describe('DashboardContentNetworkFlowDonut', () => {
  it('requests the explicit widget', async () => {
    await renderComputedWidget(DashboardContentNetworkFlowDonut, makeContentProps(CONTENT))
    await screen.findAllByText('HTTPS')

    expect(endpoint.requests).toEqual([
      { source: { type: 'explicit', content: CONTENT, context: {} } }
    ])
  })
})
