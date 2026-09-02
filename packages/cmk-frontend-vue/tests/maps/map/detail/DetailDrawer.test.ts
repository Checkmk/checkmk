/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { CommandVerb } from '@/maps/api/ticket'
import DetailDrawer from '@/maps/map/detail/DetailDrawer.vue'
import type { MapElement, ObjectState } from '@/maps/types/api'

import { aState, anObject } from '../../support/fixtures'
import {
  aTicket,
  fakeMapsServices,
  fullCapabilities,
  provideServices
} from '../../support/services'

// Every command button is gated on `auth.mayCommand(verb)`, which reads the
// capability set the session minted. Each render gets a session with exactly
// the commands under test, so the gating is exercised end to end.
const ALL_COMMANDS: CommandVerb[] = [
  'acknowledge',
  'remove_acknowledgement',
  'force_check',
  'schedule_downtime',
  'add_comment',
  'disable_notifications',
  'enable_notifications'
]

function service(extra: Partial<MapElement> = {}): MapElement {
  return anObject({
    id: 's1',
    type: 'service',
    host_name: 'web01',
    service_description: 'CPU load',
    ...extra
  })
}

function criticalState(extra: Partial<ObjectState> = {}): ObjectState {
  return aState({
    object_id: 's1',
    type: 'service',
    state: 'CRITICAL',
    output: 'CPU load too high',
    perf_data: '',
    acknowledged: false,
    in_downtime: false,
    stale: false,
    notifications_enabled: true,
    ...extra
  })
}

const stubs = { MetricChart: true }

interface DrawerProps {
  object: MapElement | null
  state?: ObjectState | undefined
  connectionId?: string | null
  checkmkUrl?: string | null
  unattended?: boolean
}

async function renderDrawer(props: DrawerProps, commands: CommandVerb[] = ALL_COMMANDS) {
  const services = fakeMapsServices({}, aTicket({ capabilities: fullCapabilities({ commands }) }))
  await services.auth.init()
  const { global: provided } = provideServices(services)
  const utils = render(DetailDrawer, {
    props,
    global: { ...provided, stubs }
  })
  if (props.object) {
    await screen.findByRole('button', { name: 'Close' })
  }
  return utils
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('DetailDrawer – header rendering', () => {
  it('renders the object name, type pill, state pill and check output', async () => {
    await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })

    // Service display name is "<host> / <service>", the type pill names the
    // object type as a person reads it, and the state pill carries the raw
    // monitoring state.
    expect(screen.getByText('web01 / CPU load')).toBeInTheDocument()
    expect(screen.getByText('Service')).toBeInTheDocument()
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
    expect(screen.getByText('CPU load too high')).toBeInTheDocument()
  })

  it('renders no drawer content when no object is selected', () => {
    render(DetailDrawer, {
      props: { object: null },
      global: { ...provideServices(fakeMapsServices()).global, stubs }
    })

    expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
    expect(screen.queryByText('web01 / CPU load')).not.toBeInTheDocument()
  })
})

describe('DetailDrawer – command-button capability gating', () => {
  it('shows the command actions for a problematic object when the user may command', async () => {
    await renderDrawer({ object: service(), state: criticalState(), connectionId: 'test' })

    expect(screen.getByRole('button', { name: 'Acknowledge' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Force check' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Schedule downtime' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add comment' })).toBeInTheDocument()
  })

  it('hides every command action when the user has no command capabilities', async () => {
    await renderDrawer({ object: service(), state: criticalState(), connectionId: 'test' }, [])

    expect(screen.queryByRole('button', { name: 'Acknowledge' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Force check' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Schedule downtime' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add comment' })).not.toBeInTheDocument()
  })

  it('hides every command action on an unattended surface even with full capabilities', async () => {
    // A kiosk wall or the settings live preview has nobody in front of it to
    // answer for a command.
    await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test',
      unattended: true
    })

    expect(screen.queryByRole('button', { name: 'Acknowledge' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Force check' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Schedule downtime' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add comment' })).not.toBeInTheDocument()
  })

  it('offers "Remove ACK" instead of "Acknowledge" once the object is acknowledged', async () => {
    await renderDrawer({
      object: service(),
      state: criticalState({ acknowledged: true }),
      connectionId: 'test'
    })

    expect(screen.queryByRole('button', { name: 'Acknowledge' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove ACK' })).toBeInTheDocument()
  })
})

describe('DetailDrawer – command emits', () => {
  it('emits the matching command event when an action button is clicked', async () => {
    const user = userEvent.setup()
    const { emitted } = await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })

    await user.click(screen.getByRole('button', { name: 'Acknowledge' }))
    await user.click(screen.getByRole('button', { name: 'Force check' }))

    expect(emitted('acknowledge')).toHaveLength(1)
    expect(emitted('force-check')).toHaveLength(1)
  })

  it('emits close when the header close button is clicked', async () => {
    const user = userEvent.setup()
    const { emitted } = await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })

    await user.click(screen.getByRole('button', { name: 'Close' }))

    expect(emitted('close')).toHaveLength(1)
  })

  it('emits close on Escape', async () => {
    const user = userEvent.setup()
    const { emitted } = await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })

    await user.keyboard('{Escape}')

    expect(emitted('close')).toHaveLength(1)
  })
})

describe('DetailDrawer – focus', () => {
  it('takes focus when it opens and hands it back when it closes', async () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()
    const { rerender } = await renderDrawer({ object: null })

    await rerender({ object: service(), state: criticalState(), connectionId: 'test' })

    const drawer = await screen.findByRole('complementary')
    await vi.waitFor(() => expect(drawer).toHaveFocus())

    await rerender({ object: null })

    expect(opener).toHaveFocus()
    opener.remove()
  })
})

describe('DetailDrawer – tabs', () => {
  it('shows the Performance tab when perf data is present and switches to it', async () => {
    const user = userEvent.setup()
    // A parseable "label=value;warn;crit;min;max" metric drives the (purely
    // derived) Performance tab; Context/Members stay hidden without fetched
    // details.
    await renderDrawer({
      object: service(),
      state: criticalState({ perf_data: 'load1=3.5;5;10;0;16' }),
      connectionId: 'test'
    })

    const statusTab = screen.getByRole('tab', { name: 'Status' })
    const performanceTab = screen.getByRole('tab', { name: 'Performance' })
    expect(statusTab).toHaveAttribute('aria-selected', 'true')
    expect(screen.queryByRole('tab', { name: 'Context' })).not.toBeInTheDocument()

    await user.click(performanceTab)

    expect(performanceTab).toHaveAttribute('aria-selected', 'true')
    expect(statusTab).toHaveAttribute('aria-selected', 'false')
  })
})
