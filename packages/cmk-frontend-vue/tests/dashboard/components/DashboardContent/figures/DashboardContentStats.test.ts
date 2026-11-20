/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { restApiHttp } from 'cmk-ui-library/vitest.msw'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import DashboardContentStats from '@/dashboard/components/DashboardContent/figures/DashboardContentStats.vue'
import { useProvideDrillDownSource } from '@/dashboard/composables/useDrillDownSource'
import type { LinkProperties, Stats, StatsContent } from '@/dashboard/types/widget'

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

const DEFERRED_SITES: LinkProperties = { links: [{ sites: { status: 'deferred' } }] }

const LINKED_HOST_STATS: Stats = {
  ...HOST_STATS,
  links: [
    {
      title: 'All hosts',
      location: { type: 'views', name: 'allhosts' },
      include_context: false,
      include_time_range: false,
      show_filter_form: false
    }
  ],
  total: { ...HOST_STATS.total, link_properties: DEFERRED_SITES }
}

const PROPS = makeContentProps<StatsContent>({
  type: 'host_stats',
  contextual_link: { type: 'default' }
})

const endpoint = useComputeWidgetEndpoint(
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

  it('leads the total to the page that values its filters, naming the dashboard it leaves', async () => {
    endpoint.answerInThisTest(LINKED_HOST_STATS)
    const dashboard = defineComponent({
      setup() {
        useProvideDrillDownSource(ref('Overview'))
        return () => h(DashboardContentStats, PROPS)
      }
    })
    render(dashboard)

    const href = (await screen.findByRole('link', { name: /Total/ })).getAttribute('href')!

    expect(href.startsWith('dashboard_stats_link.py?')).toBe(true)
    const variables = new URLSearchParams(href.split('?')[1])
    expect(variables.get('part')).toBe('total')
    expect(variables.get('_drilled_from')).toBe('Overview')
  })
})
