/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { restApiHttp } from 'cmk-ui-library/vitest.msw'
import {
  resizeObserverReporting,
  useFakeResizeObserver
} from 'cmk-ui-library/vitest.resize-observer'
import { describe, expect, it } from 'vitest'

import DashboardContentStateSummary from '@/dashboard/components/DashboardContent/figures/DashboardContentStateSummary.vue'
import type { StateSummary, StateSummaryContent } from '@/dashboard/types/widget'

import { useComputeWidgetEndpoint } from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const HOST_SUMMARY: StateSummary = {
  links: [],
  in_state: { count: 3, link_properties: { links: [] } },
  total: 10
}

const CONTENT: StateSummaryContent = { type: 'host_state_summary', state: 'DOWN' }

const endpoint = useComputeWidgetEndpoint(
  restApiHttp.post,
  '/domain-types/dashboard/actions/compute-state-summary/invoke',
  HOST_SUMMARY
)
useFakeResizeObserver(resizeObserverReporting(400, 200))

function renderWidget() {
  return render(DashboardContentStateSummary, { props: makeContentProps(CONTENT) })
}

describe('DashboardContentStateSummary', () => {
  it('requests the explicit widget', async () => {
    renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })

  it('draws the summary as delivered by the backend', async () => {
    renderWidget()

    expect(await screen.findByText('3/10')).toBeInTheDocument()
  })
})
