/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import type { MapsCommandSettings } from 'cmk-shared-typing/typescript/maps'
import { describe, expect, it, vi } from 'vitest'

import type { CommandVerb } from '@/maps/api/ticket'
import DetailDrawer from '@/maps/map/detail/DetailDrawer.vue'
import type { MapElement, ObjectState } from '@/maps/types/api'

import { aState, anObject } from '../../support/fixtures'
import {
  aCommandSettings,
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
  'remove_all_downtimes',
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

async function renderDrawer(
  props: DrawerProps,
  commands: CommandVerb[] = ALL_COMMANDS,
  settings: MapsCommandSettings = aCommandSettings()
) {
  const services = fakeMapsServices({}, aTicket({ capabilities: fullCapabilities({ commands }) }))
  await services.auth.init()
  const { global: provided } = provideServices(services, settings)
  const utils = render(DetailDrawer, {
    props,
    global: { ...provided, stubs }
  })
  if (props.object) {
    await screen.findByRole('button', { name: 'Close' })
  }
  return { ...utils, commands: services.apis.commands, toasts: services.toasts }
}

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

  it('says where the link to Checkmk leads', async () => {
    await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test',
      checkmkUrl: 'http://checkmk/site/check_mk/'
    })

    expect(
      screen.getAllByRole('link', { name: 'Open the state of web01 / CPU load in a new tab' })
    ).not.toHaveLength(0)
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

  it('offers a group only the commands Checkmk applies to a whole group', async () => {
    await renderDrawer({
      object: anObject({ id: 'g1', type: 'hostgroup', group_name: 'linux' }),
      state: aState({ object_id: 'g1', type: 'hostgroup', state: 'DOWN' }),
      connectionId: 'test',
      checkmkUrl: 'http://localhost/site/check_mk/'
    })

    expect(screen.getByRole('button', { name: /Acknowledge/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Downtime/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Force check' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add comment' })).not.toBeInTheDocument()
  })

  it('offers a group without a problem nothing to acknowledge', async () => {
    await renderDrawer({
      object: anObject({ id: 'g1', type: 'hostgroup', group_name: 'linux' }),
      state: aState({ object_id: 'g1', type: 'hostgroup', state: 'UP' }),
      connectionId: 'test',
      checkmkUrl: 'http://localhost/site/check_mk/'
    })

    expect(screen.queryByRole('button', { name: /Acknowledge/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Downtime/ })).toBeInTheDocument()
  })
})

describe('DetailDrawer – commands', () => {
  it('acknowledges through the shared form in a dialog', async () => {
    const user = userEvent.setup()
    const { commands } = await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })

    await user.click(screen.getByRole('button', { name: 'Acknowledge' }))
    const dialog = await screen.findByRole('dialog', { name: 'Acknowledge problem' })
    await user.type(within(dialog).getByRole('textbox', { name: /Comment/ }), 'On it')
    await user.click(within(dialog).getByRole('button', { name: 'Acknowledge' }))

    expect(commands.acknowledgeService).toHaveBeenCalledWith(
      'web01',
      'CPU load',
      expect.objectContaining({ comment: 'On it' })
    )
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(await screen.findByText('Acknowledgement set')).toBeInTheDocument()
  })

  it('keeps the dialog open with what Checkmk said when it refuses', async () => {
    const user = userEvent.setup()
    const { commands } = await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })
    vi.mocked(commands.addCommentService).mockRejectedValue(new Error('Host not found'))

    await user.click(screen.getByRole('button', { name: 'Add comment' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add comment' })
    await user.type(within(dialog).getByRole('textbox', { name: /Comment/ }), 'Note')
    await user.click(within(dialog).getByRole('button', { name: 'Add comment' }))

    expect(await within(dialog).findByText('Could not add the comment')).toBeInTheDocument()
    expect(within(dialog).getByText('Host not found')).toBeInTheDocument()
  })

  it("offers the site's downtime durations and repeats", async () => {
    const user = userEvent.setup()
    await renderDrawer(
      { object: service(), state: criticalState(), connectionId: 'test' },
      ALL_COMMANDS,
      aCommandSettings({
        downtime_presets: [{ title: 'Two hours', end: 7200 }],
        downtime_recurrences: [
          { recur: 'fixed', title: 'never' },
          { recur: 'week', title: 'weekly' }
        ]
      })
    )

    await user.click(screen.getByRole('button', { name: 'Schedule downtime' }))
    const dialog = await screen.findByRole('dialog', { name: 'Schedule downtime' })

    expect(within(dialog).getByRole('button', { name: 'Two hours' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  })

  it('forces a check right away, without a dialog', async () => {
    const user = userEvent.setup()
    const { commands } = await renderDrawer({
      object: service(),
      state: criticalState({ site_id: 'siteA' }),
      connectionId: 'test'
    })

    await user.click(screen.getByRole('button', { name: 'Force check' }))

    expect(commands.forceCheckService).toHaveBeenCalledWith('web01', 'CPU load', 'siteA')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('says why a command without a dialog failed', async () => {
    const user = userEvent.setup()
    const { commands } = await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })
    vi.mocked(commands.forceCheckService).mockRejectedValue(new Error('Host not found'))

    await user.click(screen.getByRole('button', { name: 'Force check' }))

    expect(await screen.findByText('Could not schedule the check')).toBeInTheDocument()
  })

  it('shows a command as running until Checkmk has taken it', async () => {
    const user = userEvent.setup()
    const { commands } = await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })
    let resolve = (): void => {}
    vi.mocked(commands.forceCheckService).mockReturnValue(
      new Promise<void>((settle) => (resolve = settle))
    )

    const button = screen.getByRole('button', { name: 'Force check' })
    await user.click(button)
    expect(button).toHaveAttribute('aria-busy', 'true')

    resolve()

    expect(await screen.findByText('Force check scheduled')).toBeInTheDocument()
    expect(button).toHaveAttribute('aria-busy', 'false')
  })

  it('does not show a command for one object as running on the next', async () => {
    const user = userEvent.setup()
    const { commands, rerender } = await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })
    vi.mocked(commands.forceCheckService).mockReturnValue(new Promise<void>(() => {}))

    await user.click(screen.getByRole('button', { name: 'Force check' }))
    await rerender({
      object: service({ id: 's2', service_description: 'Memory' }),
      state: criticalState({ object_id: 's2' })
    })

    expect(screen.getByRole('button', { name: 'Force check' })).toHaveAttribute(
      'aria-busy',
      'false'
    )
  })

  it('reports in a toast once the slide-in has closed', async () => {
    const user = userEvent.setup()
    const { commands, toasts, rerender } = await renderDrawer({
      object: service(),
      state: criticalState(),
      connectionId: 'test'
    })
    let resolve = (): void => {}
    vi.mocked(commands.forceCheckService).mockReturnValue(
      new Promise<void>((settle) => (resolve = settle))
    )

    await user.click(screen.getByRole('button', { name: 'Force check' }))
    await rerender({ object: null })
    resolve()

    await waitFor(() =>
      expect(toasts.toasts.value.map((toast) => toast.message)).toContain('Force check scheduled')
    )
  })

  it('lets its clicks reach the page, where the map closes its menus', async () => {
    const user = userEvent.setup()
    await renderDrawer({ object: service(), state: criticalState(), connectionId: 'test' })
    const onPageClick = vi.fn()
    document.addEventListener('click', onPageClick, { once: true })

    await user.click(screen.getByRole('button', { name: 'Force check' }))

    expect(onPageClick).toHaveBeenCalled()
  })

  it('offers removing the downtimes only to who may remove all of them', async () => {
    await renderDrawer(
      { object: service(), state: criticalState({ in_downtime: true }), connectionId: 'test' },
      ALL_COMMANDS.filter((verb) => verb !== 'remove_all_downtimes')
    )

    expect(screen.queryByRole('button', { name: 'Remove downtimes' })).not.toBeInTheDocument()
  })

  it('removes the downtimes only once confirmed', async () => {
    const user = userEvent.setup()
    const { commands } = await renderDrawer({
      object: service(),
      state: criticalState({ in_downtime: true }),
      connectionId: 'test',
      checkmkUrl: 'http://localhost/site/check_mk/'
    })

    await user.click(screen.getByRole('button', { name: 'Remove downtimes' }))
    expect(commands.removeDowntimeService).not.toHaveBeenCalled()

    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Remove downtimes' }))

    expect(commands.removeDowntimeService).toHaveBeenCalledWith(
      'http://localhost/site/check_mk/',
      'web01',
      'CPU load'
    )
  })
})

describe('DetailDrawer – closing', () => {
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

  it('falls back to Status when the open tab goes away', async () => {
    const user = userEvent.setup()
    const { rerender } = await renderDrawer({
      object: service(),
      state: criticalState({ perf_data: 'load1=3.5;5;10;0;16' }),
      connectionId: 'test'
    })
    await user.click(screen.getByRole('tab', { name: 'Performance' }))

    await rerender({ object: service(), state: criticalState(), connectionId: 'test' })

    expect(screen.queryByRole('tab', { name: 'Performance' })).not.toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Status' })).toHaveAttribute('aria-selected', 'true')
  })
})
