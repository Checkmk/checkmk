/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

import DashboardContentMonitoringTable from '@/dashboard/components/DashboardContent/DashboardContentMonitoringTable.vue'
import { useProvideCmkToken } from '@/dashboard/composables/useCmkToken'
import type { ComputedMonitoringTable, MonitoringTableContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'
import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/compute-monitoring-table/invoke`

const CONTENT: MonitoringTableContent = {
  type: 'monitoring_table',
  table: 'hosts',
  columns: ['state', 'name'],
  sort: ['name:asc'],
  limit: 100,
  date_format: '%Y-%m-%d',
  timestamp_format: 'mixed'
}

const VALUE: ComputedMonitoringTable = {
  table: 'hosts',
  rows: [
    {
      name: 'heute',
      state: 'UP',
      is_flapping: false,
      stale: false,
      site_id: 'heute',
      legacy_host_status_link: 'view.py?view_name=hoststatus&host=heute&site=heute'
    }
  ],
  matched: 1,
  total: 1,
  unapplied_filters: []
}

const CMK_TOKEN = '0:the-token'

let value: ComputedMonitoringTable = VALUE
let failWith: number | null = null
let requests: unknown[] = []
let authorizations: (string | null)[] = []

useMswServer(
  http.post(ENDPOINT, async ({ request }) => {
    requests.push(await request.json())
    authorizations.push(request.headers.get('Authorization'))
    if (failWith !== null) {
      return HttpResponse.json({ title: 'Internal error' }, { status: failWith })
    }
    return HttpResponse.json({ domainType: 'widget-compute', value })
  })
)

const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')

beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })
})

afterAll(() => {
  if (originalOffsetHeight) {
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight)
  }
})

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})

afterEach(() => {
  value = VALUE
  failWith = null
  requests = []
  authorizations = []
  FakeResizeObserver.instances = []
  vi.unstubAllGlobals()
})

async function renderWidget(tick = 0) {
  const rendered = render(DashboardContentMonitoringTable, {
    props: makeContentProps(CONTENT, { tick })
  })
  await nextTick()
  deliverSize(800, 400)
  return rendered
}

async function renderInSharedDashboard() {
  const wrapper = defineComponent({
    setup() {
      useProvideCmkToken(CMK_TOKEN)
      return () => h(DashboardContentMonitoringTable, makeContentProps(CONTENT))
    }
  })
  const rendered = render(wrapper)
  await nextTick()
  deliverSize(800, 400)
  return rendered
}

async function clickHeader(name: string, expectedRequests: number) {
  await userEvent.click(screen.getByRole('button', { name }))
  await waitFor(() => expect(requests).toHaveLength(expectedRequests))
}

describe('DashboardContentMonitoringTable', () => {
  it('shows the hosts the backend selects', async () => {
    await renderWidget()

    expect(await screen.findByText('heute')).toBeInTheDocument()
  })

  it('shows only the columns the widget picks', async () => {
    await renderWidget()
    await screen.findByText('heute')

    expect(screen.getAllByRole('columnheader').map((header) => header.textContent?.trim())).toEqual(
      ['State', 'Host']
    )
  })

  it('asks again in the order a click on a column header picks', async () => {
    await renderWidget()
    await screen.findByText('heute')

    await userEvent.click(screen.getByRole('button', { name: 'Host' }))

    await waitFor(() =>
      expect(requests.at(-1)).toEqual({
        source: { type: 'explicit', content: CONTENT, context: {} },
        sort: ['name:desc']
      })
    )
  })

  it('asks in the newly configured order once the sort changes', async () => {
    const { rerender } = await renderWidget()
    await screen.findByText('heute')
    await userEvent.click(screen.getByRole('button', { name: 'Host' }))
    const content: MonitoringTableContent = { ...CONTENT, sort: ['state:desc'] }

    await rerender(makeContentProps(content))

    await waitFor(() =>
      expect(requests.at(-1)).toEqual({
        source: { type: 'explicit', content, context: {} },
        sort: ['state:desc']
      })
    )
  })

  it("drops the viewer's order once the columns change", async () => {
    const { rerender } = await renderWidget()
    await screen.findByText('heute')
    await userEvent.click(screen.getByRole('button', { name: 'State' }))
    const content: MonitoringTableContent = { ...CONTENT, columns: ['name'] }

    await rerender(makeContentProps(content))

    await waitFor(() =>
      expect(requests.at(-1)).toEqual({
        source: { type: 'explicit', content, context: {} },
        sort: ['name:asc']
      })
    )
  })

  it('fetches again on a refresh tick', async () => {
    const { rerender } = await renderWidget()
    await screen.findByText('heute')

    await rerender(makeContentProps(CONTENT, { tick: 1 }))

    await waitFor(() => expect(requests).toHaveLength(2))
  })

  it('names the dashboard filters it cannot apply', async () => {
    value = {
      ...VALUE,
      unapplied_filters: [{ id: 'hostgroups', title: 'Host groups' }]
    }

    await renderWidget()

    expect(await screen.findByRole('note')).toHaveTextContent(
      'Not applied to this table: Host groups'
    )
  })

  it('goes back to the configured order on the third click on a header', async () => {
    await renderWidget()
    await screen.findByText('heute')

    await clickHeader('State', 2)
    await clickHeader('State', 3)
    await clickHeader('State', 4)

    expect(requests.at(-1)).toEqual({
      source: { type: 'explicit', content: CONTENT, context: {} },
      sort: ['name:asc']
    })
  })

  it('shows the host name as plain text, not as a button', async () => {
    await renderWidget()

    expect(await screen.findByText('heute')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'heute' })).not.toBeInTheDocument()
  })

  it('says how many hosts it leaves out beyond its limit', async () => {
    value = { ...VALUE, matched: 250, total: 300 }

    await renderWidget()

    expect(await screen.findByText('Showing 1 of 250 hosts')).toBeInTheDocument()
  })

  it('says nothing about a limit when all hosts fit', async () => {
    await renderWidget()
    await screen.findByText('heute')

    expect(screen.queryByText(/^Showing /)).not.toBeInTheDocument()
  })

  it('shows the empty state when no host matches', async () => {
    value = { ...VALUE, rows: [], matched: 0 }

    await renderWidget()

    expect(await screen.findByText('No results found.')).toBeInTheDocument()
  })

  it('offers a retry when the data cannot be loaded', async () => {
    failWith = 500

    await renderWidget()

    expect(await screen.findByText('Widget data could not be loaded.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('asks by widget ID with the token of a shared dashboard', async () => {
    await renderInSharedDashboard()
    await screen.findByText('heute')

    expect(requests.at(-1)).toEqual({
      source: { type: 'saved', widget_id: 'test-widget' },
      sort: ['name:asc']
    })
    expect(authorizations.at(-1)).toBe(`CMK-TOKEN ${CMK_TOKEN}`)
  })
})
