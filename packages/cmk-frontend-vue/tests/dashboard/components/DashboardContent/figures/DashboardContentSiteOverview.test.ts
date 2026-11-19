/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentSiteOverview from '@/dashboard/components/DashboardContent/figures/DashboardContentSiteOverview.vue'
import type { SiteOverview, SiteOverviewContent } from '@/dashboard/types/widget'

import { useComputeWidgetEndpoint } from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'
import { resizeObserverReporting, useFakeResizeObserver } from '@tests/lib/fakeResizeObserver'

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
useFakeResizeObserver(resizeObserverReporting(400, 200))

function renderWidget() {
  return render(DashboardContentSiteOverview, { props: makeContentProps(CONTENT) })
}

describe('DashboardContentSiteOverview', () => {
  it('requests the explicit widget', async () => {
    renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })

  it('draws the hosts as delivered by the backend', async () => {
    renderWidget()

    expect(await screen.findByRole('figure', { name: '1 host, 1 critical' })).toBeInTheDocument()
  })
})
