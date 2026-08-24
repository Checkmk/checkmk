/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import ServiceOverviewTab from '@/monitoring/host-services/components/slide-in/ServiceOverviewTab.vue'
import type { ServiceOverview } from '@/monitoring/shared/api/types'

const HOST_LINK = 'view.py?view_name=hoststatus&site=local&host=web-server-01'
const SERVICE_LINK = 'view.py?view_name=service&site=local&host=web-server-01&service=CPU+load'
const PARAMETERS_LINK = 'wato.py?mode=object_parameters&host=web-server-01&service=CPU+load'
const GRAPHS_LINK =
  'view.py?view_name=service_graphs&site=local&host=web-server-01&service=CPU+load'

function makeOverview(overrides: Partial<ServiceOverview> = {}): ServiceOverview {
  return {
    name: 'CPU load',
    host_name: 'web-server-01',
    site_id: 'local',
    state: 'OK',
    modes: [],
    host_alias: 'Web Server',
    host_state: 'UP',
    host_modes: [],
    legacy_host_status_link: HOST_LINK,
    legacy_service_status_link: SERVICE_LINK,
    legacy_service_parameters_link: PARAMETERS_LINK,
    legacy_service_graphs_link: GRAPHS_LINK,
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

describe('ServiceOverviewTab', () => {
  it('names the host the service belongs to, with its alias and state', () => {
    render(ServiceOverviewTab, { props: { data: makeOverview() } })

    expect(screen.getByText('web-server-01')).toBeInTheDocument()
    expect(screen.getByText('Web Server')).toBeInTheDocument()
    expect(screen.getByText('UP')).toBeInTheDocument()
  })

  it('shows the contact groups responsible for the service', () => {
    render(ServiceOverviewTab, {
      props: { data: makeOverview({ contact_groups: ['linux-admins', 'on-call'] }) }
    })

    expect(screen.getByText('linux-admins')).toBeInTheDocument()
    expect(screen.getByText('on-call')).toBeInTheDocument()
  })

  it('shows what the check reported and when', () => {
    render(ServiceOverviewTab, { props: { data: makeOverview() } })

    expect(screen.getByText('OK - load average: 0.10, 0.05, 0.01')).toBeInTheDocument()
    expect(screen.getByText('1/3')).toBeInTheDocument()
  })

  it('shows the state markers of the summary as badges', () => {
    const { container } = render(ServiceOverviewTab, {
      props: { data: makeOverview({ summary: 'load: 3.1(!), temp: 90(!!)' }) }
    })

    expect(container.querySelector('.cmk-state-tag--warning')).toHaveTextContent('WA')
    expect(container.querySelector('.cmk-state-tag--critical')).toHaveTextContent('CR')
    expect(container.textContent).toContain('load: 3.1')
  })

  it('dashes out the next check of a passive service', () => {
    render(ServiceOverviewTab, { props: { data: makeOverview({ next_check: null }) } })

    expect(screen.getByText('–')).toBeInTheDocument()
  })

  it('dashes out the last check of a service that has never been checked', () => {
    render(ServiceOverviewTab, { props: { data: makeOverview({ last_check: null }) } })

    expect(screen.getByText('–')).toBeInTheDocument()
  })

  it('keeps the long output collapsed until the panel is opened', async () => {
    render(ServiceOverviewTab, {
      props: { data: makeOverview({ long_output: '15 min load: 0.01 (per core: 0.01)' }) }
    })
    expect(screen.getByText('15 min load: 0.01 (per core: 0.01)')).not.toBeVisible()

    await userEvent.click(screen.getByRole('button', { name: /Toggle Service details/ }))

    expect(screen.getByText('15 min load: 0.01 (per core: 0.01)')).toBeVisible()
  })

  it('keeps the details panel when the plugin produced no output', async () => {
    render(ServiceOverviewTab, { props: { data: makeOverview({ long_output: '' }) } })

    await userEvent.click(screen.getByRole('button', { name: /Toggle Service details/ }))

    expect(screen.getByText('This check plugin reports no further details.')).toBeVisible()
  })

  it('shows the service tags, ordered the way the table orders them', () => {
    const { container } = render(ServiceOverviewTab, {
      props: { data: makeOverview({ tags: { networking: 'lan', criticality: 'prod' } }) }
    })

    expect(screen.getByText('criticality: prod')).toBeInTheDocument()
    expect(screen.getByText('networking: lan')).toBeInTheDocument()

    const chips = Array.from(container.querySelectorAll('.monitoring-overview-chips .cmk-tag')).map(
      (chip) => chip.textContent?.trim()
    )
    expect(chips.indexOf('criticality: prod')).toBeLessThan(chips.indexOf('networking: lan'))
  })

  it('shows the service labels with their value', () => {
    render(ServiceOverviewTab, {
      props: {
        data: makeOverview({
          labels: { 'cmk/check_plugin': { value: 'cpu_load', source: 'discovered' } }
        })
      }
    })

    expect(screen.getByText('cmk/check_plugin: cpu_load')).toBeInTheDocument()
  })

  it('keeps the tag and label rows when the service has neither', () => {
    render(ServiceOverviewTab, { props: { data: makeOverview({ tags: {}, labels: {} }) } })

    expect(screen.getByText('Tags:')).toBeInTheDocument()
    expect(screen.getByText('Labels:')).toBeInTheDocument()
  })

  it('links to the host details from the host row', () => {
    render(ServiceOverviewTab, { props: { data: makeOverview() } })

    expect(
      screen.getByRole('link', { name: 'Show details of host web-server-01' })
    ).toHaveAttribute('href', HOST_LINK)
  })

  it('shows the modes of the host next to its state', () => {
    render(ServiceOverviewTab, {
      props: {
        data: makeOverview({
          host_modes: [
            {
              icon_name: 'downtime',
              link: 'view.py?view_name=downtimes_of_host&site=local&host=web-server-01',
              title: 'Host is in scheduled downtime'
            }
          ]
        })
      }
    })

    expect(screen.getByRole('link', { name: 'Host is in scheduled downtime' })).toBeInTheDocument()
  })
})
