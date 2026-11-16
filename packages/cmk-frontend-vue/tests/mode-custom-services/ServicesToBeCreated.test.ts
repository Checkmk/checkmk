/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, within } from '@testing-library/vue'
import { expect, test } from 'vitest'

import type { ServicesToCreate } from '@/mode-custom-services/definition'
import type { ServicesPreview } from '@/mode-custom-services/servicesPreview'
import ServicesToBeCreated from '@/mode-custom-services/steps/ServicesToBeCreated.vue'

type Service = ServicesToCreate['services'][number]

function service(serviceName: string, overrides: Partial<Service> = {}): Service {
  return {
    host_name: 'web01',
    service_name: serviceName,
    new_host: false,
    clash: null,
    ...overrides
  }
}

function renderList(preview: ServicesPreview) {
  return render(ServicesToBeCreated, { props: { preview } })
}

function resolved(services: Service[], extra: Partial<ServicesToCreate> = {}): ServicesPreview {
  return {
    status: 'resolved',
    services: { services, total: services.length, clashes: [], complete: true, ...extra }
  }
}

test('numbers every service with its name and target host', () => {
  renderList(resolved([service('Latency GET'), service('Latency POST', { host_name: 'web02' })]))

  expect(screen.getByText(/Services to be created/)).toHaveTextContent('(2)')
  const [first, second] = screen.getAllByRole('listitem')
  for (const text of ['1/2', 'Latency GET', 'web01']) {
    expect(within(first!).getByText(text)).toBeTruthy()
  }
  for (const text of ['2/2', 'Latency POST', 'web02']) {
    expect(within(second!).getByText(text)).toBeTruthy()
  }
})

test('marks hosts that saving creates', () => {
  renderList(resolved([service('Latency', { host_name: 'pod-new', new_host: true })]))

  expect(screen.getByRole('listitem')).toHaveTextContent('pod-new (new host)')
})

test('flags a clashing service and explains the clash', () => {
  renderList(
    resolved(
      [service('Latency', { clash: 'own_series' }), service('Latency', { clash: 'own_series' })],
      {
        clashes: [{ host_name: 'web01', service_name: 'Latency', message: 'Group the series.' }]
      }
    )
  )

  for (const item of screen.getAllByRole('listitem')) {
    expect(within(item).getByText('Several series get this name')).toBeTruthy()
  }
  expect(screen.getByText('Group the series.').closest('[role="alert"]')).not.toBeNull()
})

test('states how many services are not listed', () => {
  renderList(resolved([service('Latency GET')], { total: 250 }))

  expect(screen.getByText('Showing the first 1 of 250 services.')).toBeTruthy()
  expect(screen.getByText(/Services to be created/)).toHaveTextContent('(250)')
})

test('tells that series appearing later are not shown', () => {
  renderList(resolved([service('Latency GET')]))

  expect(
    screen.getByText('Series appearing after saving add services that are not shown here.')
  ).toBeTruthy()
})

test('tells that a metric without series creates no service yet', () => {
  renderList(resolved([]))

  expect(screen.getByText(/currently has no series/)).toBeTruthy()
  expect(screen.queryByRole('list')).toBeNull()
})

test('shows a failed lookup with its reason', () => {
  renderList({ status: 'failed', error: 'The data backend is not reachable.' })

  expect(
    screen.getByText('The data backend is not reachable.').closest('[role="alert"]')
  ).not.toBeNull()
})

test('asks for every input the services are named from', () => {
  renderList({ status: 'idle' })

  expect(
    screen.getByText(
      'Enter a service name and select a host or enter a host name template to see the services to be created.'
    )
  ).toBeTruthy()
})

test('tells that a metric with more series than looked up creates more services', () => {
  renderList(resolved([service('Latency GET')], { complete: false }))

  expect(screen.getByText(/more series than are looked up here/)).toBeTruthy()
})
