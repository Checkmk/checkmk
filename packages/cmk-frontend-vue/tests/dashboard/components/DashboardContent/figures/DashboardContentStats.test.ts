/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { restApiHttp } from 'cmk-ui-library/vitest.msw'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import DashboardContentStats from '@/dashboard/components/DashboardContent/figures/DashboardContentStats.vue'
import type { Stats, StatsContent } from '@/dashboard/types/widget'

import { useComputeWidgetEndpoint } from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'
import { resizeObserverReporting, useFakeResizeObserver } from '@tests/lib/fakeResizeObserver'

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

useComputeWidgetEndpoint(
  restApiHttp.post,
  '/domain-types/dashboard/actions/compute-stats/invoke',
  HOST_STATS
)
useFakeResizeObserver(resizeObserverReporting(400, 200))

beforeEach(() => {
  Object.defineProperty(SVGElement.prototype, 'getBBox', {
    configurable: true,
    value: () => ({ x: 0, y: 0, width: 100, height: 60 })
  })
})
afterEach(() => {
  Reflect.deleteProperty(SVGElement.prototype, 'getBBox')
})

describe('DashboardContentStats', () => {
  it('draws the counts as delivered by the backend', async () => {
    render(DashboardContentStats, { props: PROPS })

    expect(await screen.findByRole('img', { name: 'Down: 3' })).toBeInTheDocument()
  })
})
