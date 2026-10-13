/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentState from '@/dashboard/components/DashboardContent/figures/DashboardContentState.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { ObjectState, StateContent } from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

const HOST_STATE: ObjectState = {
  links: [],
  link_properties: { links: [] },
  state: 'DOWN',
  has_been_checked: true,
  tint_background: true,
  plugin_output: null
}

const CONTENT: StateContent = {
  type: 'host_state',
  status_display: { type: 'background', for_states: 'all' },
  contextual_link: { type: 'default' }
}

const endpoint = useComputeWidgetEndpoint<ObjectState>('compute-state', () => HOST_STATE)

async function renderWidget(props: ContentProps<StateContent> = makeContentProps(CONTENT)) {
  return renderComputedWidget(DashboardContentState, props)
}

describe('DashboardContentState', () => {
  it('requests the explicit widget', async () => {
    await renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })

  it('draws the state as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByText('DOWN')).toBeInTheDocument()
  })
})
