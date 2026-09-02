/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useObjectActions } from '@/maps/map/commands/useObjectActions'
import type { MapsApis } from '@/maps/services/context'
import type { DowntimeEntry, MapElement } from '@/maps/types/api'

import { aState } from '../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../support/services'

/** Registers the state an object's command should route by. */
function seedState(objectId: string, siteId: string): void {
  services.states.states.value[objectId] = aState({
    object_id: objectId,
    type: 'host',
    state: 'UP',
    site_id: siteId
  })
}

vi.mock('cmk-ui-library/lib/i18n', () => ({
  default: () => ({ _t: (s: string) => s }),
  untranslated: (s: string) => s
}))

function hostObj(over: Partial<MapElement> = {}): MapElement {
  return { id: 'o1', type: 'host', host_name: 'web01', ...over } as MapElement
}
function serviceObj(over: Partial<MapElement> = {}): MapElement {
  return {
    id: 'o2',
    type: 'service',
    host_name: 'web01',
    service_description: 'CPU',
    ...over
  } as MapElement
}

const URL = 'https://cmk.example/site'

let services: ReturnType<typeof fakeMapsServices>
let commands: MapsApis['commands']
let refreshAfterCommand: ReturnType<typeof vi.spyOn>
let toast: { success: ReturnType<typeof vi.spyOn>; error: ReturnType<typeof vi.spyOn> }

beforeEach(() => {
  services = fakeMapsServices()
  commands = services.apis.commands
  refreshAfterCommand = vi
    .spyOn(services.states, 'refreshAfterCommand')
    .mockImplementation(() => {})
  toast = {
    success: vi.spyOn(services.toasts, 'success').mockImplementation(() => {}),
    error: vi.spyOn(services.toasts, 'error').mockImplementation(() => {})
  }
})

describe('useObjectActions — command dispatch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('routes forceCheck on a service to the service endpoint with host+service+site', async () => {
    seedState('o2', 'siteA')
    const { handlers } = runWithServices(services, () => useObjectActions(URL))
    await handlers.forceCheck(serviceObj())
    expect(vi.mocked(commands.forceCheckService)).toHaveBeenCalledWith('web01', 'CPU', 'siteA')
    expect(vi.mocked(commands.forceCheckHost)).not.toHaveBeenCalled()
    expect(toast.success).toHaveBeenCalledWith('Force check scheduled')
    expect(refreshAfterCommand).toHaveBeenCalledOnce()
  })

  it('routes forceCheck on a host to the host endpoint', async () => {
    const { handlers } = runWithServices(services, () => useObjectActions(URL))
    await handlers.forceCheck(hostObj())
    expect(vi.mocked(commands.forceCheckHost)).toHaveBeenCalledWith('web01', null)
    expect(vi.mocked(commands.forceCheckService)).not.toHaveBeenCalled()
  })

  it('prefers the live state-map site_id over the object-carried site_id', async () => {
    seedState('o1', 'live')
    const { handlers } = runWithServices(services, () => useObjectActions(URL))
    await handlers.forceCheck(hostObj({ site_id: 'stale' }))
    expect(vi.mocked(commands.forceCheckHost)).toHaveBeenCalledWith('web01', 'live')
  })

  it('falls back to the object site_id when no state-map entry exists', async () => {
    const { handlers } = runWithServices(services, () => useObjectActions(URL))
    await handlers.forceCheck(hostObj({ site_id: 'objsite' }))
    expect(vi.mocked(commands.forceCheckHost)).toHaveBeenCalledWith('web01', 'objsite')
  })

  it('does nothing for an object without a host name', async () => {
    const { handlers } = runWithServices(services, () => useObjectActions(URL))
    await handlers.forceCheck({ id: 'o1', type: 'host' } as MapElement)
    expect(vi.mocked(commands.forceCheckHost)).not.toHaveBeenCalled()
    expect(vi.mocked(commands.forceCheckService)).not.toHaveBeenCalled()
  })

  it('still issues the command without a configured Checkmk URL (GUI is same-origin)', async () => {
    const { handlers } = runWithServices(services, () => useObjectActions(null))
    await handlers.forceCheck(hostObj())
    expect(vi.mocked(commands.forceCheckHost)).toHaveBeenCalledWith('web01', null)
  })

  it('surfaces a backend error as an error toast with detail, no refresh', async () => {
    vi.mocked(commands.forceCheckHost).mockRejectedValueOnce(new Error('boom'))
    const { handlers } = runWithServices(services, () => useObjectActions(URL))
    await handlers.forceCheck(hostObj())
    expect(toast.error).toHaveBeenCalledWith('Force check failed: boom')
    expect(refreshAfterCommand).not.toHaveBeenCalled()
  })

  it('toggleNotifications picks enable vs disable endpoints', async () => {
    const { handlers } = runWithServices(services, () => useObjectActions(URL))
    await handlers.toggleNotifications(hostObj(), true)
    expect(vi.mocked(commands.enableNotificationsHost)).toHaveBeenCalled()
    await handlers.toggleNotifications(hostObj(), false)
    expect(vi.mocked(commands.disableNotificationsHost)).toHaveBeenCalled()
  })

  it('removeAck routes host vs service', async () => {
    const { handlers } = runWithServices(services, () => useObjectActions(URL))
    await handlers.removeAck(serviceObj())
    expect(vi.mocked(commands.removeAcknowledgementService)).toHaveBeenCalledWith('web01', 'CPU')
  })
})

describe('useObjectActions — modal openers', () => {
  beforeEach(() => vi.clearAllMocks())

  it('acknowledge/scheduleDowntime/addComment stash the object on their modal refs', () => {
    const onStart = vi.fn()
    const a = runWithServices(services, () => useObjectActions(URL, onStart))
    a.handlers.acknowledge(hostObj({ id: 'a' }))
    a.handlers.scheduleDowntime(hostObj({ id: 'b' }))
    a.handlers.addComment(hostObj({ id: 'c' }))
    expect(a.ackModalObject.value?.id).toBe('a')
    expect(a.downtimeModalObject.value?.id).toBe('b')
    expect(a.commentModalObject.value?.id).toBe('c')
    expect(onStart).toHaveBeenCalledTimes(3)
  })
})

describe('useObjectActions — removeDowntime', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('removes a sole downtime directly without opening the modal', async () => {
    vi.mocked(commands.listDowntimesHost).mockResolvedValueOnce([
      { id: 42, site_id: 'siteA' } as unknown as DowntimeEntry
    ])
    const a = runWithServices(services, () => useObjectActions(URL))
    await a.handlers.removeDowntime(hostObj())
    expect(vi.mocked(commands.removeDowntimeById)).toHaveBeenCalledWith(URL, 42, 'siteA')
    expect(a.removeDowntimeModal.visible).toBe(false)
    expect(toast.success).toHaveBeenCalledWith('Downtime removed')
  })

  it('opens the picker modal when several downtimes exist', async () => {
    vi.mocked(commands.listDowntimesHost).mockResolvedValueOnce([
      { id: 1, site_id: 's' },
      { id: 2, site_id: 's' }
    ] as unknown as DowntimeEntry[])
    const a = runWithServices(services, () => useObjectActions(URL))
    await a.handlers.removeDowntime(hostObj())
    expect(vi.mocked(commands.removeDowntimeById)).not.toHaveBeenCalled()
    expect(a.removeDowntimeModal.visible).toBe(true)
    expect(a.removeDowntimeModal.downtimes).toHaveLength(2)
  })

  it('reports when there are no active downtimes', async () => {
    vi.mocked(commands.listDowntimesHost).mockResolvedValueOnce([])
    const a = runWithServices(services, () => useObjectActions(URL))
    await a.handlers.removeDowntime(hostObj())
    expect(toast.error).toHaveBeenCalledWith('No active downtimes found')
    expect(vi.mocked(commands.removeDowntimeById)).not.toHaveBeenCalled()
  })
})
