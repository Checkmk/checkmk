/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentStateSummary from '@/dashboard/components/DashboardContent/figures/DashboardContentStateSummary.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { StateSummary, StateSummaryContent } from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const HOST_SUMMARY: StateSummary = {
  links: [],
  in_state: { count: 3, link_properties: { links: [] } },
  total: 10
}

const CONTENT: StateSummaryContent = { type: 'host_state_summary', state: 'DOWN' }

const endpoint = useComputeWidgetEndpoint<StateSummary>('compute-state-summary', () => HOST_SUMMARY)

async function renderWidget(props: ContentProps<StateSummaryContent> = makeContentProps(CONTENT)) {
  return renderComputedWidget(DashboardContentStateSummary, props)
}

describe('DashboardContentStateSummary', () => {
  it('requests the explicit widget', async () => {
    await renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })

  it('draws the summary as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByText('3/10')).toBeInTheDocument()
  })
})
