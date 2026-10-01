/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import DashboardContentStateSummary from '@/dashboard/components/DashboardContent/figures/DashboardContentStateSummary.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { StateSummary, StateSummaryContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'
import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/compute-state-summary/invoke`

const HOST_SUMMARY: StateSummary = {
  links: [],
  in_state: { count: 3, link_properties: { links: [] } },
  total: 10
}

const CONTENT: StateSummaryContent = { type: 'host_state_summary', state: 'DOWN' }

let answer: () => Response = () =>
  HttpResponse.json({ domainType: 'widget-compute', value: HOST_SUMMARY })
let requests: unknown[] = []

const server = setupServer(
  http.post(ENDPOINT, async ({ request }) => {
    requests.push(await request.json())
    return answer()
  })
)

async function renderWidget(props: ContentProps<StateSummaryContent> = makeContentProps(CONTENT)) {
  const rendered = render(DashboardContentStateSummary, { props })
  await nextTick()
  deliverSize(400, 200)
  return rendered
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})
afterEach(() => {
  answer = () => HttpResponse.json({ domainType: 'widget-compute', value: HOST_SUMMARY })
  requests = []
  server.resetHandlers()
  FakeResizeObserver.instances = []
  vi.unstubAllGlobals()
})
afterAll(() => server.close())

describe('DashboardContentStateSummary', () => {
  it('requests the explicit widget', async () => {
    await renderWidget()

    await waitFor(() =>
      expect(requests).toEqual([{ source: { type: 'explicit', content: CONTENT, context: {} } }])
    )
  })

  it('draws the summary as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByText('3/10')).toBeInTheDocument()
  })

  it('fetches again on a refresh tick', async () => {
    const { rerender } = await renderWidget()
    await screen.findByText('3/10')

    await rerender(makeContentProps(CONTENT, { tick: 1 }))

    await waitFor(() => expect(requests).toHaveLength(2))
  })

  it('shows the no-data notice on a 404', async () => {
    answer = () => HttpResponse.json({ title: 'No data available', status: 404 }, { status: 404 })

    await renderWidget()

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })
})
