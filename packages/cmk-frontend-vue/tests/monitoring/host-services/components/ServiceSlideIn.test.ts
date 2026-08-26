/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { ExplainThisIssueData } from 'cmk-shared-typing/typescript/ai_button'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ServiceSlideIn from '@/monitoring/host-services/components/ServiceSlideIn.vue'
import type { HostRef, HostServiceEntry, ServiceOverview } from '@/monitoring/shared/api/types'
import type { ActionFeedback } from '@/monitoring/shared/components/action/ActionFeedback.vue'
import { ACK_ACTION_ID } from '@/monitoring/shared/components/action/actions/acknowledge'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

const HOST: HostRef = { site_id: 'local', name: 'web-server-01' }

const PERMITTED_ACTIONS: CellAction[] = [
  { id: ACK_ACTION_ID, label: 'Acknowledge problem' as TranslatedString, icon: 'ack' },
  { id: RESCHEDULE_ACTION_ID, label: 'Reschedule check' as TranslatedString, icon: 'reload' }
]

const SUCCESS: ActionFeedback = { variant: 'success', message: 'Done' as TranslatedString }

function makeActionRegistry(
  perform: (targets: string[]) => Promise<ActionFeedback> = async () => SUCCESS
): MonitoringActionRegistry<string> {
  const action = (id: string, title: string) => ({
    id,
    title: title as TranslatedString,
    submitLabel: title as TranslatedString,
    defaultValues: () => ({}),
    perform: (targets: string[]) => perform(targets)
  })
  return {
    [ACK_ACTION_ID]: action(ACK_ACTION_ID, 'Acknowledge problem'),
    [RESCHEDULE_ACTION_ID]: action(RESCHEDULE_ACTION_ID, 'Reschedule check')
  }
}

function makeService(overrides: Partial<HostServiceEntry> = {}): HostServiceEntry {
  return {
    name: 'CPU load',
    state: 'OK',
    is_flapping: false,
    stale: false,
    summary: 'OK - load average: 0.10, 0.05, 0.01',
    last_check: 1783942710,
    last_state_change: 1783942740,
    ...overrides
  }
}

function makeOverview(overrides: Partial<ServiceOverview> = {}): ServiceOverview {
  return {
    name: 'CPU load',
    host_name: HOST.name,
    site_id: HOST.site_id,
    state: 'OK',
    modes: [],
    host_alias: 'Web Server',
    host_state: 'UP',
    host_modes: [],
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=web-server-01',
    legacy_service_status_link:
      'view.py?view_name=service&site=local&host=web-server-01&service=CPU+load',
    legacy_service_parameters_link:
      'wato.py?mode=object_parameters&host=web-server-01&service=CPU+load',
    legacy_service_graphs_link:
      'view.py?view_name=service_graphs&site=local&host=web-server-01&service=CPU+load',
    contact_groups: ['all'],
    summary: 'OK - load average: 0.10, 0.05, 0.01',
    long_output: '',
    last_check: 1783942710,
    last_state_change: 1783942740,
    current_attempt: 1,
    max_check_attempts: 3,
    next_check: 1783942800,
    tags: {},
    labels: {},
    ...overrides
  }
}

describe('ServiceSlideIn', () => {
  beforeEach(() => {
    vi.spyOn(client, 'GET').mockResolvedValue({
      data: makeOverview(),
      error: undefined,
      response: new Response()
    } as never)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('stays closed while no service is selected', () => {
    render(ServiceSlideIn, { props: { service: null, host: HOST } })

    expect(screen.queryByText('Service details')).not.toBeInTheDocument()
  })

  it('shows the overview of the selected service once it is loaded', async () => {
    render(ServiceSlideIn, { props: { service: makeService(), host: HOST } })

    expect(await screen.findByText('Service details')).toBeInTheDocument()
    expect(await screen.findByText('CPU load')).toBeInTheDocument()
  })

  it('requests the overview for the selected service of this host', async () => {
    render(ServiceSlideIn, { props: { service: makeService({ name: 'Memory' }), host: HOST } })

    await screen.findByText('Service details')

    expect(client.GET).toHaveBeenCalledWith('/monitor/hosts/{hostname}/service', {
      params: {
        path: { hostname: 'web-server-01' },
        query: { site_id: 'local', service_name: 'Memory' }
      }
    })
  })

  it('reloads the overview when another service is picked while the panel is open', async () => {
    const { rerender } = render(ServiceSlideIn, {
      props: { service: makeService(), host: HOST }
    })
    await screen.findByText('Service details')

    await rerender({ service: makeService({ name: 'Memory' }), host: HOST })

    expect(client.GET).toHaveBeenLastCalledWith('/monitor/hosts/{hostname}/service', {
      params: {
        path: { hostname: 'web-server-01' },
        query: { site_id: 'local', service_name: 'Memory' }
      }
    })
  })

  it('shows the mode icons in the header once the overview has loaded', async () => {
    vi.spyOn(client, 'GET').mockResolvedValue({
      data: makeOverview({
        modes: [
          {
            icon_name: 'ack',
            link: 'view.py?view_name=service&site=local&host=web-server-01&service=CPU+load',
            title: 'Problem acknowledged'
          }
        ]
      }),
      error: undefined,
      response: new Response()
    } as never)
    render(ServiceSlideIn, { props: { service: makeService(), host: HOST } })

    expect(await screen.findByRole('link', { name: 'Problem acknowledged' })).toBeInTheDocument()
  })

  it('lets a stale overview lose the race against the service now on screen', async () => {
    let resolveStale: () => void = () => {}
    const stale = new Promise((resolve) => {
      resolveStale = () =>
        resolve({
          data: makeOverview({
            modes: [
              {
                icon_name: 'ack',
                link: 'view.py?view_name=service&site=local&host=web-server-01&service=CPU+load',
                title: 'Problem acknowledged'
              }
            ]
          }),
          error: undefined,
          response: new Response()
        })
    })
    vi.spyOn(client, 'GET')
      .mockReturnValueOnce(stale as never)
      .mockResolvedValue({
        data: makeOverview({ name: 'Memory' }),
        error: undefined,
        response: new Response()
      } as never)

    const { rerender } = render(ServiceSlideIn, {
      props: { service: makeService(), host: HOST }
    })
    await rerender({ service: makeService({ name: 'Memory' }), host: HOST })

    resolveStale()
    // Let every pending microtask run, so the stale response really does get its chance to win.
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(screen.queryByRole('link', { name: 'Problem acknowledged' })).not.toBeInTheDocument()
  })

  it('offers the service details and parameters as icon buttons in the header', async () => {
    render(ServiceSlideIn, { props: { service: makeService(), host: HOST } })

    expect(
      await screen.findByRole('link', { name: 'Show details of service CPU load' })
    ).toHaveAttribute(
      'href',
      'view.py?view_name=service&site=local&host=web-server-01&service=CPU+load'
    )
    expect(screen.getByRole('link', { name: 'Parameters of this service' })).toHaveAttribute(
      'href',
      'wato.py?mode=object_parameters&host=web-server-01&service=CPU+load'
    )
  })

  it('offers the actions the user may run on the service', async () => {
    render(ServiceSlideIn, {
      props: {
        service: makeService(),
        host: HOST,
        actions: makeActionRegistry(),
        permittedActions: PERMITTED_ACTIONS
      }
    })

    expect(await screen.findByRole('button', { name: 'Acknowledge problem' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reschedule check' })).toBeInTheDocument()
  })

  it('shows no action buttons to a user who may run none of them', async () => {
    render(ServiceSlideIn, {
      props: { service: makeService(), host: HOST, actions: makeActionRegistry() }
    })
    await screen.findByText('Service details')

    expect(screen.queryByRole('button', { name: 'Acknowledge problem' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reschedule check' })).not.toBeInTheDocument()
  })

  it('leaves out a permitted action this page cannot perform', async () => {
    render(ServiceSlideIn, {
      props: {
        service: makeService(),
        host: HOST,
        actions: makeActionRegistry(),
        permittedActions: [
          ...PERMITTED_ACTIONS,
          {
            id: 'send_custom_notification',
            label: 'Send custom notification' as TranslatedString,
            icon: 'notifications'
          }
        ]
      }
    })

    await screen.findByRole('button', { name: 'Acknowledge problem' })

    expect(
      screen.queryByRole('button', { name: 'Send custom notification' })
    ).not.toBeInTheDocument()
  })

  it('performs a reschedule on the shown service right away', async () => {
    const performed: string[][] = []
    render(ServiceSlideIn, {
      props: {
        service: makeService(),
        host: HOST,
        actions: makeActionRegistry(async (targets) => {
          performed.push(targets)
          return SUCCESS
        }),
        permittedActions: PERMITTED_ACTIONS
      }
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Reschedule check' }))

    expect(performed).toEqual([['CPU load']])
    expect(await screen.findByText('Done')).toBeInTheDocument()
  })

  it('opens the form of an action that needs input instead of performing it', async () => {
    const performed: string[][] = []
    render(ServiceSlideIn, {
      props: {
        service: makeService(),
        host: HOST,
        actions: makeActionRegistry(async (targets) => {
          performed.push(targets)
          return SUCCESS
        }),
        permittedActions: PERMITTED_ACTIONS
      }
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Acknowledge problem' }))

    expect(performed).toEqual([])
    expect(
      await screen.findByRole('button', { name: 'Back to service detail view' })
    ).toBeInTheDocument()
  })

  it('hides the parameters button from users who may not see rulesets', async () => {
    vi.spyOn(client, 'GET').mockResolvedValue({
      data: makeOverview({ legacy_service_parameters_link: null }),
      error: undefined,
      response: new Response()
    } as never)
    render(ServiceSlideIn, { props: { service: makeService(), host: HOST } })

    await screen.findByRole('link', { name: 'Show details of service CPU load' })

    expect(
      screen.queryByRole('link', { name: 'Parameters of this service' })
    ).not.toBeInTheDocument()
  })

  it('offers no AI explanation outside the cloud edition', async () => {
    render(ServiceSlideIn, { props: { service: makeService(), host: HOST } })
    await screen.findByText('Service details')

    expect(screen.queryByTestId('service-ai-explain-button')).not.toBeInTheDocument()
  })

  it('asks the AI app to explain the shown service', async () => {
    const explainRequests: ExplainThisIssueData[] = []
    const listener = (event: Event) => {
      explainRequests.push((event as CustomEvent<ExplainThisIssueData>).detail)
    }
    document.addEventListener('cmk-ai-explain-button', listener)
    render(ServiceSlideIn, {
      props: { service: makeService(), host: HOST, aiExplain: true }
    })

    await userEvent.click(await screen.findByTestId('service-ai-explain-button'))
    document.removeEventListener('cmk-ai-explain-button', listener)

    expect(explainRequests).toEqual([
      {
        host_name: 'web-server-01',
        service_name: 'CPU load',
        service_state: 'OK',
        host_state: 'Up'
      }
    ])
  })

  it('waits for the overview before offering the AI explanation', () => {
    vi.spyOn(client, 'GET').mockReturnValue(new Promise(() => {}) as never)
    render(ServiceSlideIn, {
      props: { service: makeService(), host: HOST, aiExplain: true }
    })

    expect(screen.queryByTestId('service-ai-explain-button')).not.toBeInTheDocument()
  })

  it('offers no action menu to a page that provides no loader for it', async () => {
    render(ServiceSlideIn, { props: { service: makeService(), host: HOST } })
    await screen.findByText('Service details')

    expect(screen.queryByRole('button', { name: 'More actions' })).not.toBeInTheDocument()
  })

  it('loads the action menu of the service on show, not before', async () => {
    const loadActionMenu = vi.fn(async () => [
      {
        id: 'logwatch',
        label: 'Open log file viewer' as TranslatedString,
        icon: 'services' as const,
        url: 'view.py?view_name=logwatch&host=web-server-01'
      }
    ])
    render(ServiceSlideIn, {
      props: { service: makeService({ name: 'Memory' }), host: HOST, loadActionMenu }
    })
    await screen.findByText('Service details')
    expect(loadActionMenu).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'More actions' }))

    expect(loadActionMenu).toHaveBeenCalledWith('Memory')
    expect(await screen.findByRole('menuitem', { name: /Open log file viewer/ })).toHaveAttribute(
      'href',
      'view.py?view_name=logwatch&host=web-server-01'
    )
  })

  it('offers a History tab next to Overview, with Overview still shown first', async () => {
    render(ServiceSlideIn, { props: { service: makeService(), host: HOST } })
    await screen.findByText('Service details')

    const tabs = screen.getAllByRole('tab').map((tab) => tab.textContent?.trim())

    expect(tabs).toEqual(['Overview', 'History', 'Service graphs'])
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
  })

  it('loads the history of that one service when its tab is activated', async () => {
    vi.spyOn(client, 'GET').mockImplementation(((url: string) =>
      Promise.resolve(
        url === '/monitor/hosts/{hostname}/events'
          ? {
              data: {
                events: [],
                meta: {
                  limit: 500,
                  truncated: false,
                  since: Math.floor(Date.now() / 1000) - 8 * 24 * 60 * 60,
                  legacy_events_link:
                    'view.py?view_name=svcevents&site=local&host=web-server-01&service=CPU+load'
                }
              },
              error: undefined,
              response: new Response()
            }
          : { data: makeOverview(), error: undefined, response: new Response() }
      )) as never)
    render(ServiceSlideIn, { props: { service: makeService(), host: HOST } })
    await screen.findByText('Service details')

    await userEvent.click(screen.getByRole('tab', { name: 'History' }))

    expect(client.GET).toHaveBeenCalledWith('/monitor/hosts/{hostname}/events', {
      params: {
        path: { hostname: 'web-server-01' },
        query: { site_id: 'local', service_name: 'CPU load' }
      }
    })
    expect(
      await screen.findByText('This service has no events in the last 8 days.')
    ).toBeInTheDocument()
  })

  it('emits close when the close button is used', async () => {
    const { emitted } = render(ServiceSlideIn, { props: { service: makeService(), host: HOST } })
    await screen.findByText('Service details')

    await userEvent.click(screen.getByRole('button', { name: 'Close' }))

    expect(emitted()['close']).toHaveLength(1)
  })
})
