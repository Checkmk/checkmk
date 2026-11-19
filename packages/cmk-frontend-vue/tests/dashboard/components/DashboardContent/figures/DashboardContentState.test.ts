/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentState from '@/dashboard/components/DashboardContent/figures/DashboardContentState.vue'
import type { HostOrServiceState, StateContent } from '@/dashboard/types/widget'

import { useComputeWidgetEndpoint } from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'
import { resizeObserverReporting, useFakeResizeObserver } from '@tests/lib/fakeResizeObserver'

const HOST_STATE: HostOrServiceState = {
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

const endpoint = useComputeWidgetEndpoint<HostOrServiceState>('compute-state', () => HOST_STATE)
useFakeResizeObserver(resizeObserverReporting(400, 200))

function renderWidget() {
  return render(DashboardContentState, { props: makeContentProps(CONTENT) })
}

describe('DashboardContentState', () => {
  it('requests the explicit widget', async () => {
    renderWidget()

    await waitFor(() =>
      expect(endpoint.requests).toEqual([
        { source: { type: 'explicit', content: CONTENT, context: {} } }
      ])
    )
  })

  it('draws the state as delivered by the backend', async () => {
    renderWidget()

    expect(await screen.findByText('DOWN')).toBeInTheDocument()
  })
})
