/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentNetworkFlowTopTable from '@/dashboard/components/DashboardContent/NetworkFlow/DashboardContentNetworkFlowTopTable.vue'
import type {
  ComputedNetworkFlowTopTable,
  NetworkFlowTopTableContent
} from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const CONTENT: NetworkFlowTopTableContent = {
  type: 'network_flow_top_table',
  dimension: 'local_hosts',
  accent: 'blue',
  limit_to: 10
}

const endpoint = useComputeWidgetEndpoint<ComputedNetworkFlowTopTable>(
  'compute-network-flow-top-table',
  () => ({
    columns: [{ key: 'host', title: 'Host', render: 'text', bar: false }],
    rows: [{ host: '10.0.0.1' }]
  })
)

describe('DashboardContentNetworkFlowTopTable', () => {
  it('requests the explicit widget', async () => {
    await renderComputedWidget(DashboardContentNetworkFlowTopTable, makeContentProps(CONTENT))
    await screen.findByText('10.0.0.1')

    expect(endpoint.requests).toEqual([
      { source: { type: 'explicit', content: CONTENT, context: {} } }
    ])
  })
})
