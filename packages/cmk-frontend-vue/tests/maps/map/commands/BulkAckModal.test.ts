/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import BulkAckModal from '@/maps/map/commands/BulkAckModal.vue'
import type { MapsApis } from '@/maps/services/context'
import type { BulkAckTarget } from '@/maps/types/api'

import { fakeMapsServices, provideServices } from '../../support/services'

function target(host: string, service: string | null = null): BulkAckTarget {
  return { host, service }
}

function renderModal(targets: BulkAckTarget[]) {
  return render(BulkAckModal, {
    ...provideServices(services),
    props: { aggregationId: 'agg-1', targets, checkmkUrl: 'https://cmk.example.com/site' }
  })
}

async function clickSubmit(targetCount: number) {
  const user = userEvent.setup()
  // The dialog content teleports into the document body a tick after mount.
  await user.click(await screen.findByRole('button', { name: `Acknowledge ${targetCount} leaves` }))
}

let services: ReturnType<typeof fakeMapsServices>
let commands: MapsApis['commands']

beforeEach(() => {
  vi.clearAllMocks()
  services = fakeMapsServices()
  commands = services.apis.commands
})

describe('BulkAckModal', () => {
  it('pre-fills the comment with the aggregation trailer', async () => {
    renderModal([target('web01')])
    expect(await screen.findByRole('textbox')).toHaveValue('Bulk-ack: agg-1')
  })

  it('lists every target', async () => {
    renderModal([target('web01', 'PING'), target('db02')])
    const items = await screen.findAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('web01')
    expect(items[0]).toHaveTextContent('PING')
  })

  it('routes each leaf to host or service ack', async () => {
    renderModal([target('web01', 'PING'), target('db02')])
    await clickSubmit(2)
    await waitFor(() => expect(commands.acknowledgeService).toHaveBeenCalledTimes(1))
    // Host/service acks route by site id, not the base URL (only group acks take
    // the URL); the bulk targets carry no site, so no routing arg is passed.
    const options = { comment: 'Bulk-ack: agg-1', sticky: true, notify: true, persistent: false }
    expect(commands.acknowledgeService).toHaveBeenCalledWith('web01', 'PING', options)
    expect(commands.acknowledgeHost).toHaveBeenCalledTimes(1)
    expect(commands.acknowledgeHost).toHaveBeenCalledWith('db02', options)
  })

  it('acknowledges every target even beyond the concurrency cap', async () => {
    const targets = Array.from({ length: 12 }, (_, i) => target(`h${i}`))
    renderModal(targets)
    await clickSubmit(12)
    await waitFor(() => expect(commands.acknowledgeHost).toHaveBeenCalledTimes(12))
    await screen.findByText('12 leaves acknowledged')
  })

  it('reports partial failures without aborting the rest', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.mocked(commands.acknowledgeHost).mockRejectedValueOnce(new Error('pipe closed'))
    renderModal([target('bad'), target('good')])
    await clickSubmit(2)
    await waitFor(() => expect(commands.acknowledgeHost).toHaveBeenCalledTimes(2))
    // The failure summary names the failed target in its sample list.
    await screen.findByText(/1 of 2 failed: bad/)
    warn.mockRestore()
  })
})
