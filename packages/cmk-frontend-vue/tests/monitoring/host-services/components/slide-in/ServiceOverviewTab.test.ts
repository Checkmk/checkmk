/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import ServiceOverviewTab from '@/monitoring/host-services/components/slide-in/ServiceOverviewTab.vue'
import type { ServiceOverview } from '@/monitoring/shared/api/types'

const HOST_LINK = 'view.py?view_name=hoststatus&site=local&host=web-server-01'
const SERVICE_LINK = 'view.py?view_name=service&site=local&host=web-server-01&service=CPU+load'
const PARAMETERS_LINK = 'wato.py?mode=object_parameters&host=web-server-01&service=CPU+load'

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
    contact_groups: ['all'],
    summary: 'OK - load average: 0.10, 0.05, 0.01',
    long_output: '',
    last_check: '2026-07-13T11:38:30Z',
    last_state_change: '2026-07-13T11:39:00Z',
    current_attempt: 1,
    max_check_attempts: 3,
    next_check: '2026-07-13T11:40:00Z',
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

  it('links to the host details', () => {
    render(ServiceOverviewTab, { props: { data: makeOverview() } })

    expect(screen.getByRole('link', { name: 'Show host details' })).toHaveAttribute(
      'href',
      HOST_LINK
    )
  })

  it('links to the service details', () => {
    render(ServiceOverviewTab, { props: { data: makeOverview() } })

    expect(screen.getByRole('link', { name: 'Show service details' })).toHaveAttribute(
      'href',
      SERVICE_LINK
    )
  })
})
