/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentBarplot from '@/dashboard/components/DashboardContent/figures/DashboardContentBarplot.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { Barplot, BarplotContent } from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const BARPLOT: Barplot = {
  links: [],
  unit_format: {
    notation: 'decimal',
    symbol: '%',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  },
  range: null,
  bars: [
    {
      site_id: 'heute',
      host_name: 'myhost',
      service_description: 'CPU utilization',
      value: 40,
      link_properties: { links: [] }
    }
  ]
}

const CONTENT: BarplotContent = {
  type: 'barplot',
  metric: 'util',
  display_range: 'automatic',
  contextual_link: { type: 'default' }
}

const endpoint = useComputeWidgetEndpoint<Barplot>('compute-barplot', () => BARPLOT)

async function renderWidget(props: ContentProps<BarplotContent> = makeContentProps(CONTENT)) {
  return renderComputedWidget(DashboardContentBarplot, props)
}

describe('DashboardContentBarplot', () => {
  it('requests the explicit widget', async () => {
    await renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })

  it('draws the bars as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByRole('img', { name: 'myhost: 40%' })).toBeInTheDocument()
  })
})
