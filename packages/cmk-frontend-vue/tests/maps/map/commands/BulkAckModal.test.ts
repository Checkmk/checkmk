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
import type { CommandTarget } from '@/maps/types/api'

import { fakeMapsServices, provideServices } from '../../support/services'

function target(
  host: string,
  service: string | null = null,
  site: string | null = null
): CommandTarget {
  return { host, service, site }
}

function renderModal(targets: CommandTarget[], skipped = 0) {
  return render(BulkAckModal, {
    ...provideServices(services),
    props: { origin: 'agg-1', targets, skipped }
  })
}

async function clickSubmit(targetCount: number) {
  const user = userEvent.setup()
  // The dialog content teleports into the document body a tick after mount.
  await user.click(await screen.findByRole('button', { name: `Acknowledge ${targetCount}` }))
}

let services: ReturnType<typeof fakeMapsServices>
let commands: MapsApis['commands']

beforeEach(() => {
  vi.clearAllMocks()
  services = fakeMapsServices()
  commands = services.apis.commands
})

describe('BulkAckModal', () => {
  it('says how many of the picked were left out for having no problem', async () => {
    renderModal([target('web01')], 2)
    expect(await screen.findByText('2 without a problem left out')).toBeInTheDocument()
  })

  it('pre-fills the comment with where the targets came from', async () => {
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

  it('routes each target to host or service ack', async () => {
    renderModal([target('web01', 'PING', 'remote'), target('db02')])
    await clickSubmit(2)
    await waitFor(() => expect(commands.acknowledgeService).toHaveBeenCalledTimes(1))
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
    await screen.findByText('12 acknowledged')
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

  it('tries again only on what refused, never on what already took it', async () => {
    // An acknowledgement does not collapse when repeated, so re-sending it to a
    // host that took the first one would leave it acknowledged twice.
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.mocked(commands.acknowledgeHost).mockRejectedValueOnce(new Error('pipe closed'))
    renderModal([target('bad'), target('good')])

    await clickSubmit(2)
    await screen.findByText(/1 of 2 failed: bad/)

    // The button now offers the one that refused, not the whole selection.
    await clickSubmit(1)
    await waitFor(() => expect(commands.acknowledgeHost).toHaveBeenCalledTimes(3))
    expect(vi.mocked(commands.acknowledgeHost).mock.calls.map((call) => call[0])).toEqual([
      'bad',
      'good',
      'bad'
    ])
    // Counted across both runs: what the operator wants to know is how much of
    // their selection is acknowledged now.
    await screen.findByText('2 acknowledged')
    warn.mockRestore()
  })
})
