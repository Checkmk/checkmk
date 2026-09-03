/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { HostEntry } from '@/monitoring/shared/api/types'
import HostHeader from '@/monitoring/shared/components/HostHeader.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionButtons.vue'

beforeAll(() => {
  // reka-ui's menu interactions rely on pointer-capture APIs that jsdom does not implement.
  window.HTMLElement.prototype.hasPointerCapture = () => false
  window.HTMLElement.prototype.setPointerCapture = () => {}
  window.HTMLElement.prototype.releasePointerCapture = () => {}
})

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'web-1',
    state: 'UP',
    is_flapping: false,
    stale: false,
    address: '10.0.0.1',
    alias: 'web server 1',
    site_id: 'local',
    num_services: 6,
    num_services_ok: 6,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=web-1',
    num_relations: 0,
    ...overrides
  }
}

const INLINE_ACTIONS: CellAction[] = [
  {
    id: 'show_status',
    label: 'Show status of host web-1' as TranslatedString,
    icon: 'folder',
    url: 'view.py?view_name=hoststatus&site=local&host=web-1'
  },
  {
    id: 'edit',
    label: 'Edit host web-1' as TranslatedString,
    icon: 'edit',
    url: 'wato.py?mode=edit_host&host=web-1'
  }
]

test('renders the host state badge and name', () => {
  render(HostHeader, { props: { host: makeHost() } })

  expect(screen.getByText('UP')).toBeInTheDocument()
  expect(screen.getByText('web-1')).toBeInTheDocument()
})

test('renders the host name as plain text when no url is given', () => {
  render(HostHeader, { props: { host: makeHost() } })

  expect(screen.queryByRole('link', { name: 'web-1' })).not.toBeInTheDocument()
})

test('links the host name to the given url', () => {
  render(HostHeader, { props: { host: makeHost(), url: 'monitor_all_hosts.py#host=web-1' } })

  expect(screen.getByRole('link', { name: 'web-1' })).toHaveAttribute(
    'href',
    'monitor_all_hosts.py#host=web-1'
  )
})

test('renders the mode icons ahead of the host name', () => {
  render(HostHeader, {
    props: {
      host: makeHost({
        modes: [
          {
            icon_name: 'downtime',
            link: 'view.py?view_name=downtimes_of_host&host=web-1',
            title: 'In scheduled downtime'
          }
        ]
      })
    }
  })

  const downtime = screen.getByRole('link', { name: 'In scheduled downtime' })
  expect(downtime).toHaveAttribute('href', 'view.py?view_name=downtimes_of_host&host=web-1')
  expect(downtime.compareDocumentPosition(screen.getByText('web-1'))).toBe(
    Node.DOCUMENT_POSITION_FOLLOWING
  )
})

test('shows a flapping badge between the state and the host name', () => {
  render(HostHeader, { props: { host: makeHost({ is_flapping: true }) } })

  const flapping = screen.getByTitle('Flapping')
  expect(flapping.compareDocumentPosition(screen.getByText('UP'))).toBe(
    Node.DOCUMENT_POSITION_PRECEDING
  )
  expect(flapping.compareDocumentPosition(screen.getByText('web-1'))).toBe(
    Node.DOCUMENT_POSITION_FOLLOWING
  )
})

test('shows a stale badge when the host is stale', () => {
  render(HostHeader, { props: { host: makeHost({ stale: true }) } })

  expect(screen.getByTitle('Stale')).toBeInTheDocument()
})

test('shows neither badge for a host that is neither flapping nor stale', () => {
  render(HostHeader, { props: { host: makeHost() } })

  expect(screen.queryByTitle('Flapping')).not.toBeInTheDocument()
  expect(screen.queryByTitle('Stale')).not.toBeInTheDocument()
})

test('renders the inline actions as links with their host-specific tooltips', () => {
  render(HostHeader, { props: { host: makeHost(), actions: INLINE_ACTIONS } })

  expect(screen.getByRole('link', { name: 'Show status of host web-1' })).toHaveAttribute(
    'href',
    'view.py?view_name=hoststatus&site=local&host=web-1'
  )
  expect(screen.getByRole('link', { name: 'Edit host web-1' })).toHaveAttribute(
    'href',
    'wato.py?mode=edit_host&host=web-1'
  )
})

test('emits command with the host when a menu command entry is selected', async () => {
  const load = vi.fn(
    async (): Promise<CellAction[]> => [
      { id: 'reschedule', label: 'Reschedule check' as TranslatedString, icon: 'reload' }
    ]
  )
  const { emitted } = render(HostHeader, {
    props: { host: makeHost(), actions: INLINE_ACTIONS, loadActionMenu: load }
  })

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
  await userEvent.click(await screen.findByRole('menuitem', { name: /Reschedule check/ }))

  expect(emitted('command')).toEqual([
    [{ id: 'reschedule', host: { site_id: 'local', name: 'web-1' } }]
  ])
})
