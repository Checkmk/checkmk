/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import DashboardContentStats from '@/dashboard/components/DashboardContent/figures/DashboardContentStats.vue'
import type { Stats, StatsContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'
import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/compute-stats/invoke`

const HOST_STATS: Stats = {
  links: [],
  parts: [
    { category: 'up', count: 12, link_properties: { links: [] } },
    { category: 'downtime', count: 0, link_properties: { links: [] } },
    { category: 'unreachable', count: 0, link_properties: { links: [] } },
    { category: 'down', count: 3, link_properties: { links: [] } }
  ],
  total: { count: 15, link_properties: { links: [] } }
}

const PROPS = makeContentProps<StatsContent>({
  type: 'host_stats',
  contextual_link: { type: 'default' }
})

let answer: () => Response = () =>
  HttpResponse.json({ domainType: 'widget-compute', value: HOST_STATS })

const server = setupServer(http.post(ENDPOINT, () => answer()))

async function renderWidget(): Promise<void> {
  render(DashboardContentStats, { props: PROPS })
  await nextTick()
  deliverSize(400, 200)
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
  Object.defineProperty(SVGElement.prototype, 'getBBox', {
    configurable: true,
    value: () => ({ x: 0, y: 0, width: 100, height: 60 })
  })
})
afterEach(() => {
  Reflect.deleteProperty(SVGElement.prototype, 'getBBox')
  answer = () => HttpResponse.json({ domainType: 'widget-compute', value: HOST_STATS })
  server.resetHandlers()
  FakeResizeObserver.instances = []
})
afterAll(() => server.close())

describe('DashboardContentStats', () => {
  it('draws the counts as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByRole('img', { name: 'Down: 3' })).toBeInTheDocument()
  })

  it('shows the no-data notice on a 404', async () => {
    answer = () => HttpResponse.json({ title: 'No data available', status: 404 }, { status: 404 })

    await renderWidget()

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })
})
