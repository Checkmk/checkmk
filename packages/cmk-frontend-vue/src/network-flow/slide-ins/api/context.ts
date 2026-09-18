/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { NetworkFlowDonutContent, VisualContext } from '@/dashboard/types/widget'

export type ComputedNetworkFlowHost = components['schemas']['ComputedNetworkFlowHost']
export type ComputedNetworkFlowAutonomousSystem =
  components['schemas']['ComputedNetworkFlowAutonomousSystem']
export type ComputedNetworkFlowDonutOtherBreakdown =
  components['schemas']['ComputedNetworkFlowDonutOtherBreakdown']

const CONTENT_TYPE_HEADER = { params: { header: { 'Content-Type': 'application/json' } } }

/**
 * The detail panels' data.
 *
 * The endpoints still live under /domain-types/dashboard/, where they were added:
 * they are read by the flow explorer as well now, so re-homing them under
 * /network_flow/ is a separate cleanup.
 */
export const networkFlowContextApi = {
  hostContext: async (ip: string): Promise<ComputedNetworkFlowHost> => {
    const response = unwrap(
      await client.POST(
        '/domain-types/dashboard/actions/compute-network-flow-host-context/invoke',
        {
          ...CONTENT_TYPE_HEADER,
          body: { ip }
        }
      )
    )
    return response.value
  },
  /** The categories behind a donut's aggregated "Other" slice, over `window`. */
  donutOtherBreakdown: async (
    content: NetworkFlowDonutContent,
    context: VisualContext,
    window: { start: number; end: number }
  ): Promise<ComputedNetworkFlowDonutOtherBreakdown> => {
    const response = unwrap(
      await client.POST(
        '/domain-types/dashboard/actions/compute-network-flow-donut-other-breakdown/invoke',
        {
          ...CONTENT_TYPE_HEADER,
          body: { content, context, window }
        }
      )
    )
    return response.value
  },
  autonomousSystemContext: async (asn: number): Promise<ComputedNetworkFlowAutonomousSystem> => {
    const response = unwrap(
      await client.POST(
        '/domain-types/dashboard/actions/compute-network-flow-autonomous-system-context/invoke',
        {
          ...CONTENT_TYPE_HEADER,
          body: { asn }
        }
      )
    )
    return response.value
  }
}
