/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'

import FolderBulkActionModal from '@/maps/map/foldertree/components/FolderBulkActionModal.vue'
import type { MapsApis } from '@/maps/services/context'
import type { FolderTreeNode } from '@/maps/types/api'

import { aFolderNode } from '../../support/fixtures'
import {
  aTicket,
  fakeMapsServices,
  fullCapabilities,
  provideServices
} from '../../support/services'

function aHost(title: string, overrides: Partial<FolderTreeNode> = {}): FolderTreeNode {
  return aFolderNode({ path: `/main/rack-1/${title}`, title, kind: 'host', ...overrides })
}

function aRack(...hosts: FolderTreeNode[]): FolderTreeNode {
  return aFolderNode({ path: '/main/rack-1', title: 'rack-1', children: hosts })
}

/** A rack of hosts that are all down, so every one of them has something to acknowledge. */
function aRackOf(...hosts: string[]): FolderTreeNode {
  return aRack(...hosts.map((title) => aHost(title, { state: 'DOWN' })))
}

async function renderModal(folder: FolderTreeNode): Promise<MapsApis['commands']> {
  const services = fakeMapsServices(
    {},
    aTicket({ capabilities: fullCapabilities({ commands: ['acknowledge'] }) })
  )
  await services.auth.init()
  render(FolderBulkActionModal, { ...provideServices(services), props: { folder } })
  return services.apis.commands
}

describe('FolderBulkActionModal', () => {
  it('acknowledges every host in the folder', async () => {
    const user = userEvent.setup()
    const commands = await renderModal(aRackOf('web01', 'db01'))

    // The dialog content teleports into the document body a tick after mount.
    await user.type(await screen.findByRole('textbox'), 'rack maintenance')
    await user.click(screen.getByRole('button', { name: 'Acknowledge 2 hosts' }))

    await waitFor(() => expect(commands.acknowledgeHost).toHaveBeenCalledTimes(2))
  })

  it('leaves out the hosts without a problem, judged by their own state', async () => {
    // Checkmk refuses to acknowledge a host that has none, and a tile that is red
    // for a failing service can belong to a host that is UP.
    const user = userEvent.setup()
    const commands = await renderModal(
      aRack(
        aHost('web01', { state: 'DOWN' }),
        aHost('db01', { state: 'CRITICAL', own_state: 'UP' })
      )
    )

    await screen.findByText('1 host that is up left out.')
    await user.type(screen.getByRole('textbox'), 'rack maintenance')
    await user.click(screen.getByRole('button', { name: 'Acknowledge 1 host' }))

    await waitFor(() => expect(commands.acknowledgeHost).toHaveBeenCalledTimes(1))
    expect(vi.mocked(commands.acknowledgeHost).mock.calls[0]![0]).toBe('web01')
  })

  it('says why there is nothing to acknowledge where no host is down', async () => {
    // Every host is up and red for its services: "Acknowledge 0 hosts" would
    // be a button that can never be pressed.
    await renderModal(aRack(aHost('web01', { state: 'WARNING', own_state: 'UP' })))

    expect(
      await screen.findByText(/No host in “rack-1” is down or unreachable/)
    ).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('points to the sub-folders where only they hold a host that is down', async () => {
    const user = userEvent.setup()
    await renderModal(
      aRack(
        aHost('web01'),
        aFolderNode({
          path: '/main/rack-1/shelf',
          title: 'shelf',
          children: [aHost('db01', { state: 'DOWN' })]
        })
      )
    )

    await user.click(await screen.findByRole('checkbox', { name: 'Include sub-folders' }))

    expect(
      await screen.findByText(/No host directly in “rack-1” is down or unreachable/)
    ).toBeInTheDocument()
  })

  it('offers only what refused after a partial failure, not the whole folder', async () => {
    // A retry re-sends what refused, so a button still offering the folder count
    // would promise an acknowledgement of hosts that already took theirs.
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const user = userEvent.setup()
    const commands = await renderModal(aRackOf('web01', 'web02', 'db01'))
    vi.mocked(commands.acknowledgeHost).mockRejectedValueOnce(new Error('pipe closed'))

    await user.type(await screen.findByRole('textbox'), 'rack maintenance')
    await user.click(screen.getByRole('button', { name: 'Acknowledge 3 hosts' }))
    await screen.findByText(/1 of 3 failed: web01/)

    await user.click(await screen.findByRole('button', { name: 'Acknowledge 1 host' }))
    await waitFor(() => expect(commands.acknowledgeHost).toHaveBeenCalledTimes(4))
    expect(vi.mocked(commands.acknowledgeHost).mock.calls.map((call) => call[0])).toEqual([
      'web01',
      'web02',
      'db01',
      'web01'
    ])
    warn.mockRestore()
  })
})
