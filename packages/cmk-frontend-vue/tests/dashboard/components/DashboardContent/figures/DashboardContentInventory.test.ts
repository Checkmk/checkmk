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

import DashboardContentInventory from '@/dashboard/components/DashboardContent/figures/DashboardContentInventory.vue'
import type { InventoryAttribute, InventoryContent } from '@/dashboard/types/widget'

import { useComputeWidgetEndpoint } from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const ATTRIBUTE: InventoryAttribute = {
  links: [],
  link_properties: { links: [] },
  value: '8'
}

const CONTENT: InventoryContent = {
  type: 'inventory',
  path: '.hardware.cpu.cores',
  contextual_link: { type: 'default' }
}

const endpoint = useComputeWidgetEndpoint(
  restApiHttp.post,
  '/domain-types/dashboard/actions/compute-inventory/invoke',
  ATTRIBUTE
)
useFakeResizeObserver(resizeObserverReporting(400, 200))

function renderWidget() {
  return render(DashboardContentInventory, { props: makeContentProps(CONTENT) })
}

describe('DashboardContentInventory', () => {
  it('requests the explicit widget', async () => {
    renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })

  it('draws the attribute as delivered by the backend', async () => {
    renderWidget()

    expect(await screen.findByText('8')).toBeInTheDocument()
  })
})
