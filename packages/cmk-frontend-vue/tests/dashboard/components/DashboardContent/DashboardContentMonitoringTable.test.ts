/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
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
      legacy_host_status_link: 'view.py?view_name=hoststatus&host=heute&site=heute',
      setup_access: true
    }
  ],
  matched: 1,
  total: 1,
  unapplied_filters: [],
  unreachable_sites: [],
  actions: [{ ident: 'reschedule', title: 'Reschedule', icon: 'reload' }],
  links: [
    { ident: 'edit', title: 'Edit host', icon: 'edit', url: 'wato.py?mode=edit_host&host={host}' }
  ],
  host_actions: [],
  host_links: []
}

const SERVICES_CONTENT: MonitoringTableContent = {
  ...CONTENT,
  table: 'services',
  columns: ['host_name', 'name', 'summary'],
  sort: []
}

const SERVICES_VALUE: ComputedMonitoringTable = {
  ...VALUE,
  table: 'services',
  rows: [
    {
      name: 'Check_MK',
      host_name: 'today',
      site_id: 'today',
      host_state: 'UP',
      state: 'OK',
      is_flapping: false,
      stale: false,
      summary: '[agent] Success',
      last_check: null,
      last_state_change: null,
      reschedule: {
        label: "Reschedule 'Check_MK' service",
        tooltip: "Reschedule 'Check_MK' service",
        icon_name: 'reload-cmk',
        target: 'Check_MK'
      }
    }
  ],
  links: []
}

const CMK_TOKEN = '0:the-token'

let value: ComputedMonitoringTable = VALUE
let failWith: number | null = null
let requests: unknown[] = []
let authorizations: (string | null)[] = []
let reschedules: unknown[] = []

const server = useMswServer(
  http.post(ENDPOINT, async ({ request }) => {
    requests.push(await request.json())
    authorizations.push(request.headers.get('Authorization'))
    if (failWith !== null) {
      return HttpResponse.json({ title: 'Internal error' }, { status: failWith })
    }
    return HttpResponse.json({ domainType: 'widget-compute', value })
  }),
  restApiHttp.get('/monitor/hosts/{hostname}/action_menu', ({ response }) =>
    response(200).json({ items: [] })
  ),
  restApiHttp.get('/monitor/hosts/{hostname}/service/action_menu', ({ response }) =>
    response(200).json({ items: [] })
  ),
  restApiHttp.post('/monitor/hosts/actions/reschedule', async ({ request, response }) => {
    reschedules.push(await request.json())
    return response(200).json({ rescheduled: 1, scheduled_at: 1_800_000_000, wait_timeout: 10 })
  }),
  restApiHttp.post('/monitor/services/actions/reschedule', async ({ request, response }) => {
    reschedules.push(await request.json())
    return response(200).json({ rescheduled: 1, scheduled_at: 1_800_000_000, wait_timeout: 10 })
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
  reschedules = []
  FakeResizeObserver.instances = []
  vi.unstubAllGlobals()
})

async function renderWidget(content: MonitoringTableContent = CONTENT) {
  const rendered = render(DashboardContentMonitoringTable, {
    props: makeContentProps(content)
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

  it('shows the columns the widget picks, followed by the row actions', async () => {
    await renderWidget()
    await screen.findByText('heute')

    expect(screen.getAllByRole('columnheader').map((header) => header.textContent?.trim())).toEqual(
      ['State', 'Host', 'Actions']
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

  it('names the sites that cannot be reached', async () => {
    value = { ...VALUE, unreachable_sites: ['remote_1'] }

    await renderWidget()

    expect(
      await screen.findByText('No data could be retrieved from site remote_1.')
    ).toBeInTheDocument()
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

  it('shows every service value under its own header, whatever order the columns have', async () => {
    value = SERVICES_VALUE
    await renderWidget({ ...SERVICES_CONTENT, columns: ['host_name', 'summary', 'name'] })
    await screen.findByText('Check_MK')

    const headers = screen.getAllByRole('columnheader').map((header) => header.textContent?.trim())
    const cells = screen.getAllByRole('cell').map((cell) => cell.textContent?.trim())
    expect(Object.fromEntries(headers.map((header, index) => [header, cells[index]]))).toEqual({
      Service: 'Check_MK',
      Summary: '[agent] Success',
      Host: expect.stringContaining('today'),
      Actions: ''
    })
  })

  it('shows the host of a service as text, not as a link', async () => {
    value = SERVICES_VALUE
    await renderWidget(SERVICES_CONTENT)
    await screen.findByText('Check_MK')

    expect(screen.getByRole('cell', { name: /today/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /today/ })).not.toBeInTheDocument()
  })

  it('keeps its links from navigating away in the wizard preview', async () => {
    value = { ...VALUE, rows: [{ ...VALUE.rows[0]!, num_services: 3 }] }
    render(DashboardContentMonitoringTable, {
      props: makeContentProps(
        { ...CONTENT, columns: ['name', 'num_services'] },
        { isPreview: true }
      )
    })
    await nextTick()
    deliverSize(800, 400)

    const click = new MouseEvent('click', { bubbles: true, cancelable: true })
    ;(await screen.findByRole('link', { name: '3' })).dispatchEvent(click)

    expect(click.defaultPrevented).toBe(true)
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

  it('links a host into Setup', async () => {
    await renderWidget()

    expect(await screen.findByRole('link', { name: 'Edit host' })).toHaveAttribute(
      'href',
      'wato.py?mode=edit_host&host=heute'
    )
  })

  it('reschedules the host picked in its row menu', async () => {
    await renderWidget()
    await screen.findByText('heute')

    await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Reschedule' }))

    await waitFor(() =>
      expect(reschedules).toEqual([
        { hosts: [{ site_id: 'heute', name: 'heute' }], spread_minutes: 5 }
      ])
    )
  })

  it('tells that the host picked in its row menu was rescheduled', async () => {
    const { emitted } = await renderWidget()
    await screen.findByText('heute')

    await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Reschedule' }))

    await waitFor(() =>
      expect(emitted()['actionOutcome']).toEqual([
        [{ variant: 'success', message: 'Rescheduled 1 check' }]
      ])
    )
  })

  it('tells that the host picked in its row menu could not be rescheduled', async () => {
    server.use(
      restApiHttp.post('/monitor/hosts/actions/reschedule', ({ response }) =>
        response.untyped(HttpResponse.json({ title: 'Internal error' }, { status: 500 }))
      )
    )
    const { emitted } = await renderWidget()
    await screen.findByText('heute')

    await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Reschedule' }))

    await waitFor(() =>
      expect(emitted()['actionOutcome']).toEqual([
        [
          {
            variant: 'error',
            heading: 'Could not reschedule the checks for the selected hosts',
            message: 'Retry the command. If it keeps failing, check whether the site is running.'
          }
        ]
      ])
    )
  })

  it('reschedules the service a service row names', async () => {
    value = SERVICES_VALUE
    await renderWidget(SERVICES_CONTENT)
    await screen.findByText('Check_MK')

    await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: /Reschedule 'Check_MK'/ }))

    await waitFor(() =>
      expect(reschedules).toEqual([
        {
          services: [{ site_id: 'today', host_name: 'today', name: 'Check_MK' }],
          spread_minutes: 5
        }
      ])
    )
  })

  it('offers no row actions in the wizard preview', async () => {
    render(DashboardContentMonitoringTable, {
      props: makeContentProps(CONTENT, { isPreview: true })
    })
    await nextTick()
    deliverSize(800, 400)
    await screen.findByText('heute')

    expect(screen.queryByRole('button', { name: 'More actions' })).not.toBeInTheDocument()
  })

  it('offers no row actions in a shared dashboard', async () => {
    await renderInSharedDashboard()
    await screen.findByText('heute')

    expect(screen.queryByRole('button', { name: 'More actions' })).not.toBeInTheDocument()
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
