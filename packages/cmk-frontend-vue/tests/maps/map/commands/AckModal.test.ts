/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CommandsApi } from '@/maps/api/commands'
import AckModal from '@/maps/map/commands/AckModal.vue'
import type { MapElement } from '@/maps/types/api'

import { anObject } from '../../support/fixtures'
import { type SeenRequest, snapshot, useMswServer } from '../../support/http'
import { fakeMapsServices, provideServices } from '../../support/services'

const CHECKMK_URL = 'https://cmk.example.com/site'

function obj(extra: Partial<MapElement> = {}): MapElement {
  return anObject({ id: 'o', type: 'host', url_target: '', host_name: 'web01', ...extra })
}

function renderModal(object: MapElement) {
  return render(AckModal, {
    ...provideServices(services),
    props: { object, checkmkUrl: CHECKMK_URL }
  })
}

async function submitWithComment(comment = 'fixing it') {
  const user = userEvent.setup()
  // The dialog content teleports into the document body a tick after mount.
  await user.type(await screen.findByRole('textbox'), comment)
  await user.click(screen.getByRole('button', { name: 'Acknowledge' }))
}

vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
  const { interceptableRestClient } = await import('../../support/http')
  return interceptableRestClient(await importOriginal<Record<string, unknown>>())
})

const server = useMswServer()

let services: ReturnType<typeof fakeMapsServices>
let seen: SeenRequest[]

/** The real api on an intercepted network, so the request itself is the subject. */
beforeEach(() => {
  seen = []
  services = fakeMapsServices({ apis: { commands: new CommandsApi() } })
  const record = async ({ request }: { request: Request }) => {
    seen.push(await snapshot(request))
    return HttpResponse.json({})
  }
  server.use(
    http.post('*/domain-types/acknowledge/collections/host', record),
    http.post('*/domain-types/acknowledge/collections/service', record)
  )
})

describe('AckModal submit routing', () => {
  it('acknowledges a host through the Checkmk endpoint on the page site', async () => {
    renderModal(obj({ type: 'host', host_name: 'web01' }))
    await submitWithComment()

    await waitFor(() => expect(seen).toHaveLength(1))
    expect(seen[0]!.url.pathname).toBe('/api/internal/domain-types/acknowledge/collections/host')
    expect(JSON.parse(seen[0]!.body)).toEqual({
      acknowledge_type: 'host',
      host_name: 'web01',
      comment: 'fixing it',
      sticky: true,
      notify: true,
      persistent: false
    })
  })

  it('acknowledges a service', async () => {
    renderModal(obj({ type: 'service', host_name: 'web01', service_description: 'PING' }))
    await submitWithComment()

    await waitFor(() => expect(seen).toHaveLength(1))
    expect(seen[0]!.url.pathname).toMatch(/domain-types\/acknowledge\/collections\/service$/)
    expect(JSON.parse(seen[0]!.body)).toMatchObject({
      acknowledge_type: 'service',
      host_name: 'web01',
      service_description: 'PING'
    })
  })

  it('acknowledges a hostgroup through the group endpoint of the addressed site', async () => {
    renderModal(obj({ type: 'hostgroup', group_name: 'linux', host_name: null }))
    await submitWithComment()

    await waitFor(() => expect(seen).toHaveLength(1))
    expect(seen[0]!.url.href).toBe(
      `${CHECKMK_URL}/check_mk/api/1.0/domain-types/acknowledge/collections/host`
    )
    expect(JSON.parse(seen[0]!.body)).toEqual({
      acknowledge_type: 'hostgroup',
      hostgroup_name: 'linux',
      comment: 'fixing it',
      sticky: true,
      notify: true,
      persistent: false
    })
  })

  it('acknowledges a servicegroup through the group endpoint', async () => {
    renderModal(obj({ type: 'servicegroup', group_name: 'db', host_name: null }))
    await submitWithComment()

    await waitFor(() => expect(seen).toHaveLength(1))
    expect(seen[0]!.url.pathname).toMatch(/domain-types\/acknowledge\/collections\/service$/)
    expect(JSON.parse(seen[0]!.body)).toMatchObject({
      acknowledge_type: 'servicegroup',
      servicegroup_name: 'db'
    })
  })
})

describe('AckModal validation + feedback', () => {
  it('does not submit with an empty comment', async () => {
    const user = userEvent.setup()
    renderModal(obj())
    const ackButton = await screen.findByRole('button', { name: 'Acknowledge' })
    expect(ackButton).toBeDisabled()
    await user.click(ackButton)
    expect(seen).toHaveLength(0)
  })

  it('shows a success message after acknowledging', async () => {
    renderModal(obj())
    await submitWithComment()
    await screen.findByText('Acknowledgement set')
  })

  it('does not acknowledge twice while the post-success auto-close is pending', async () => {
    const user = userEvent.setup()
    renderModal(obj({ type: 'host', host_name: 'web01' }))
    await user.type(await screen.findByRole('textbox'), 'fixing it')
    const ackButton = screen.getByRole('button', { name: 'Acknowledge' })
    await user.click(ackButton)
    await screen.findByText('Acknowledgement set')
    // The button stays disabled during the ~1.2s auto-close window, so a second
    // click can't fire a duplicate acknowledge.
    expect(ackButton).toBeDisabled()
    await user.click(ackButton)
    expect(seen).toHaveLength(1)
  })

  it('surfaces an error and appends the group hint for unconfigured groups', async () => {
    server.use(
      http.post('*/domain-types/acknowledge/collections/host', () =>
        HttpResponse.json(
          { title: 'Bad Request', detail: 'These fields have problems: hostgroup_name' },
          { status: 400 }
        )
      )
    )
    renderModal(obj({ type: 'hostgroup', group_name: 'adhoc', host_name: null }))
    await submitWithComment()

    await screen.findByText(/hostgroup_name/)
    await screen.findByText(/Setup → Host groups/)
  })
})
