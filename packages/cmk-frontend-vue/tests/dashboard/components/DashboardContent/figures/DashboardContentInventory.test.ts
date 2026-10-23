/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentInventory from '@/dashboard/components/DashboardContent/figures/DashboardContentInventory.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { InventoryAttribute, InventoryContent } from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
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

const endpoint = useComputeWidgetEndpoint<InventoryAttribute>('compute-inventory', () => ATTRIBUTE)

async function renderWidget(props: ContentProps<InventoryContent> = makeContentProps(CONTENT)) {
  return renderComputedWidget(DashboardContentInventory, props)
}

describe('DashboardContentInventory', () => {
  it('requests the explicit widget', async () => {
    await renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })

  it('draws the attribute as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByText('8')).toBeInTheDocument()
  })
})
