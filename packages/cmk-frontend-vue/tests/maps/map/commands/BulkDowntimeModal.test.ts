/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import BulkDowntimeModal from '@/maps/map/commands/BulkDowntimeModal.vue'
import type { MapsApis } from '@/maps/services/context'
import type { CommandTarget } from '@/maps/types/api'

import { fakeMapsServices, provideServices } from '../../support/services'

function target(host: string, service: string | null = null): CommandTarget {
  return { host, service, site: null }
}

function renderModal(targets: CommandTarget[]) {
  return render(BulkDowntimeModal, {
    ...provideServices(services),
    props: { origin: 'core switch', targets }
  })
}

async function typeComment() {
  // The dialog content teleports into the document body a tick after mount.
  await userEvent.type(await screen.findByPlaceholderText('What is the occasion?'), 'switch swap')
}

let commands: MapsApis['commands']
let services: ReturnType<typeof fakeMapsServices>

beforeEach(() => {
  services = fakeMapsServices()
  commands = services.apis.commands
})

describe('BulkDowntimeModal', () => {
  it('schedules every target for the same window', async () => {
    renderModal([target('web01', 'CPU'), target('db02')])

    await typeComment()
    await userEvent.click(screen.getByRole('button', { name: 'Schedule downtime for 2' }))

    await waitFor(() => expect(commands.downtimeHost).toHaveBeenCalledTimes(1))
    const service = vi.mocked(commands.downtimeService).mock.calls[0]![2]
    const host = vi.mocked(commands.downtimeHost).mock.calls[0]![1]
    expect(host).toEqual(service)
    expect(host).toMatchObject({ comment: 'switch swap', durationMinutes: 0, recur: 'fixed' })
  })

  it('takes the child hosts of the picked hosts in when asked to', async () => {
    vi.mocked(commands.childHosts).mockResolvedValue(['access01'])
    renderModal([target('core01')])

    await typeComment()
    await userEvent.click(screen.getByRole('button', { name: /Advanced option/ }))
    await userEvent.click(
      screen.getByRole('checkbox', { name: 'Only for hosts: Set child hosts in downtime.' })
    )
    await userEvent.click(screen.getByRole('button', { name: 'Schedule downtime for 1' }))

    await waitFor(() => expect(commands.downtimeHost).toHaveBeenCalledTimes(2))
    expect(commands.childHosts).toHaveBeenCalledWith(null, ['core01'])
    expect(vi.mocked(commands.downtimeHost).mock.calls.map((call) => call[0])).toEqual([
      'core01',
      'access01'
    ])
  })
})
