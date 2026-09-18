/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import ServiceSlideInHeader from '@/monitoring/host-services/components/slide-in/ServiceSlideInHeader.vue'
import type { HostServiceEntry, ServiceMode } from '@/monitoring/shared/api/types'

function makeService(overrides: Partial<HostServiceEntry> = {}): HostServiceEntry {
  return {
    name: 'CPU load',
    state: 'CRIT',
    is_flapping: false,
    stale: false,
    summary: 'CRIT - load average: 9.10, 8.05, 7.01',
    last_check: 1783942710,
    last_state_change: 1783942740,
    ...overrides
  }
}

const DOWNTIME: ServiceMode = {
  icon_name: 'downtime',
  link: 'view.py?view_name=downtimes_of_service&host=web-server-01&service=CPU+load',
  title: 'In scheduled downtime'
}

describe('ServiceSlideInHeader', () => {
  it('shows the service name and its state', () => {
    render(ServiceSlideInHeader, { props: { service: makeService() } })

    expect(screen.getByText('CPU load')).toBeInTheDocument()
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
  })

  it('shows the name and state before the modes have loaded', () => {
    render(ServiceSlideInHeader, { props: { service: makeService() } })

    expect(screen.getByText('CPU load')).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('renders a mode icon linking to its legacy view', () => {
    render(ServiceSlideInHeader, { props: { service: makeService(), modes: [DOWNTIME] } })

    expect(screen.getByRole('link', { name: 'In scheduled downtime' })).toHaveAttribute(
      'href',
      DOWNTIME.link
    )
  })

  it('renders the mode icons ahead of the service name', () => {
    render(ServiceSlideInHeader, { props: { service: makeService(), modes: [DOWNTIME] } })

    const downtime = screen.getByRole('link', { name: 'In scheduled downtime' })
    expect(downtime.compareDocumentPosition(screen.getByText('CPU load'))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
  })

  it('shows a flapping badge between the state and the service name', () => {
    render(ServiceSlideInHeader, { props: { service: makeService({ is_flapping: true }) } })

    const flapping = screen.getByTitle('Flapping')
    expect(flapping.compareDocumentPosition(screen.getByText('CRITICAL'))).toBe(
      Node.DOCUMENT_POSITION_PRECEDING
    )
    expect(flapping.compareDocumentPosition(screen.getByText('CPU load'))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    )
  })

  it('shows a stale badge when the service is stale', () => {
    render(ServiceSlideInHeader, { props: { service: makeService({ stale: true }) } })

    expect(screen.getByTitle('Stale')).toBeInTheDocument()
  })

  it('shows neither badge for a service that is neither flapping nor stale', () => {
    render(ServiceSlideInHeader, { props: { service: makeService() } })

    expect(screen.queryByTitle('Flapping')).not.toBeInTheDocument()
    expect(screen.queryByTitle('Stale')).not.toBeInTheDocument()
  })
})
