/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentSiteOverview from '@/dashboard/components/DashboardContent/figures/DashboardContentSiteOverview.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { SiteOverview, SiteOverviewContent } from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const VALUE: SiteOverview = {
  mode: 'hosts',
  links: [],
  hosts: [
    {
      site_id: 'heute',
      host_name: 'alpha',
      state: 'UP',
      has_been_checked: true,
      in_downtime: false,
      num_services: 3,
      num_warn: 0,
      num_crit: 1,
      num_unknown: 0,
      link_properties: { links: [] }
    }
  ]
}

const CONTENT: SiteOverviewContent = {
  type: 'site_overview',
  dataset: 'hosts',
  hexagon_size: 'default',
  contextual_link: { type: 'default' }
}

const endpoint = useComputeWidgetEndpoint<SiteOverview>('compute-site-overview', () => VALUE)

async function renderWidget(props: ContentProps<SiteOverviewContent> = makeContentProps(CONTENT)) {
  return renderComputedWidget(DashboardContentSiteOverview, props)
}

describe('DashboardContentSiteOverview', () => {
  it('requests the explicit widget', async () => {
    await renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })

  it('draws the hosts as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByRole('figure', { name: '1 host, 1 critical' })).toBeInTheDocument()
  })
})
