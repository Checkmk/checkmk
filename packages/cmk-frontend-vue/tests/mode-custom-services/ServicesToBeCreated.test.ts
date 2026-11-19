/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { expect, test } from 'vitest'

import type { ServicesToCreate } from '@/mode-custom-services/definition'
import type { CreatableFolder, NewHostFolders } from '@/mode-custom-services/newHostFolders'
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

test('marks each target host as to be created or existing', () => {
  renderList(
    resolved([
      service('Latency', { host_name: 'pod-new', new_host: true }),
      service('Latency', { host_name: 'web01' })
    ])
  )

  const [created, existing] = screen.getAllByRole('listitem')
  expect(within(created!).getByText('To be created')).toBeTruthy()
  expect(within(created!).queryByText('Existing')).toBeNull()
  expect(within(existing!).getByText('Existing')).toBeTruthy()
  expect(within(existing!).queryByText('To be created')).toBeNull()
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

const FOLDERS: CreatableFolder[] = [
  { path: '/', title: 'Main' },
  { path: '/k8s/shop', title: 'Main / K8s / Shop' }
]

function renderWithFolders(preview: ServicesPreview, newHostFolders: NewHostFolders) {
  return render(ServicesToBeCreated, { props: { preview, folders: FOLDERS, newHostFolders } })
}

test('the first service of a new host chooses its folder, the others name it', async () => {
  renderWithFolders(
    resolved([
      service('Latency GET', { host_name: 'pod-new', new_host: true }),
      service('Latency POST', { host_name: 'pod-new', new_host: true }),
      service('Latency GET')
    ]),
    { 'pod-new': '/k8s/shop' }
  )

  const [first, second, existing] = screen.getAllByRole('listitem')
  const folder = within(first!).getByRole('combobox', { name: 'Folder of pod-new' })
  await waitFor(() => expect(folder).toHaveTextContent('Main / K8s / Shop'))
  expect(within(second!).queryByRole('combobox')).toBeNull()
  expect(within(second!).getByText('Main / K8s / Shop')).toBeTruthy()
  expect(within(existing!).queryByText('Folder:')).toBeNull()
})

test('choosing a folder passes it on for its host', async () => {
  const { emitted } = renderWithFolders(
    resolved([service('Latency', { host_name: 'pod-new', new_host: true })]),
    { 'pod-new': '/' }
  )

  await userEvent.click(screen.getByRole('combobox', { name: 'Folder of pod-new' }))
  await userEvent.click(await screen.findByRole('option', { name: 'Main / K8s / Shop' }))

  expect(emitted('chooseFolder')).toEqual([[['pod-new'], '/k8s/shop']])
})

test('new hosts none of the listed services is on get one folder together', async () => {
  const { emitted } = renderWithFolders(
    resolved([service('Latency', { host_name: 'pod-a', new_host: true })], { total: 3 }),
    { 'pod-a': '/', 'pod-b': '/', 'pod-c': '/' }
  )

  expect(screen.getByText('2 more new hosts are created in')).toBeTruthy()
  await userEvent.click(screen.getByRole('combobox', { name: 'Folder of the other new hosts' }))
  await userEvent.click(await screen.findByRole('option', { name: 'Main / K8s / Shop' }))

  expect(emitted('chooseFolder')).toEqual([[['pod-b', 'pod-c'], '/k8s/shop']])
})

test('the other new hosts in several folders show no single folder', async () => {
  renderWithFolders(resolved([service('Latency', { host_name: 'web01' })], { total: 1 }), {
    'pod-a': '/k8s/shop',
    'pod-b': '/'
  })

  const folder = screen.getByRole('combobox', { name: 'Folder of the other new hosts' })
  expect(screen.getByText('2 new hosts are created in')).toBeTruthy()
  await waitFor(() => expect(folder).toHaveTextContent('Several folders'))
})

test('the folder of the new hosts can still be chosen while the services cannot be looked up', () => {
  renderWithFolders(
    { status: 'failed', error: 'The data backend is not reachable.' },
    {
      'pod-a': '/k8s/shop'
    }
  )

  expect(screen.getByText('1 new host is created in')).toBeTruthy()
  expect(screen.getByRole('combobox', { name: 'Folder of the other new hosts' })).toBeTruthy()
})

test('a host the services list does not show as new chooses its folder below the list', () => {
  renderWithFolders(resolved([service('Latency', { host_name: 'pod-x' })]), { 'pod-x': '/' })

  expect(within(screen.getByRole('listitem')).queryByRole('combobox')).toBeNull()
  expect(screen.getByText('1 new host is created in')).toBeTruthy()
})

test('services looked up again for other folders stay listed with their folder choice', () => {
  const services = [service('Latency', { host_name: 'pod-new', new_host: true })]
  renderWithFolders(
    { status: 'refreshing', services: { services, total: 1, clashes: [], complete: true } },
    { 'pod-new': '/k8s/shop' }
  )

  expect(screen.getByText('Updating…')).toBeTruthy()
  expect(screen.getByRole('combobox', { name: 'Folder of pod-new' })).toBeTruthy()
})

test('new hosts go to Main when the folders to create them in could not be looked up', () => {
  render(ServicesToBeCreated, {
    props: {
      preview: resolved([service('Latency', { host_name: 'pod-new', new_host: true })]),
      foldersNotLookedUp: true
    }
  })

  expect(screen.getByText(/new hosts go to the Main folder/)).toBeTruthy()
})

test('new hosts may go to Main unasked when the list does not show all services', () => {
  render(ServicesToBeCreated, {
    props: { preview: resolved([service('Latency')], { total: 2 }), foldersNotLookedUp: true }
  })

  expect(screen.getByText(/new hosts go to the Main folder/)).toBeTruthy()
})

test('no folder note while the services create no host', () => {
  render(ServicesToBeCreated, {
    props: { preview: resolved([service('Latency')]), foldersNotLookedUp: true }
  })

  expect(screen.queryByText(/the Main folder/)).toBeNull()
})
