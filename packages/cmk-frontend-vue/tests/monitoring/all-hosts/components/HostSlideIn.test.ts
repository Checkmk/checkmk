/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h as createElement, defineComponent, markRaw } from 'vue'

import HostSlideIn from '@/monitoring/all-hosts/components/HostSlideIn.vue'
import type { HostEntry, HostOverview } from '@/monitoring/shared/api/types'
import type { ActionFeedback } from '@/monitoring/shared/components/action/ActionFeedback.vue'
import { ACK_ACTION_ID } from '@/monitoring/shared/components/action/actions/acknowledge'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import { ACTION_REFRESH_DELAY_MS } from '@/monitoring/shared/constants'
import type { DisplayOptions } from '@/monitoring/shared/types'

const DISPLAY_OPTIONS: DisplayOptions = { dateFormat: '%Y-%m-%d', timestampFormat: 'abs' }

const RUNNING_CLASS = 'cmk-button--running'
const RESCHEDULE_LABEL = 'Reschedule check'
const ACK_LABEL = 'Acknowledge problem'

const SUCCESS: ActionFeedback = { variant: 'success', message: untranslated('Rescheduled') }

const STUB_FORM = markRaw(
  defineComponent({
    props: { modelValue: { type: Object, default: () => ({}) } },
    emits: ['update:modelValue', 'update:valid'],
    setup: () => () => createElement('div')
  })
)

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'host-1',
    state: 'UP',
    is_flapping: false,
    stale: false,
    address: '10.0.0.1',
    alias: 'host 1',
    site_id: 'local',
    num_services: 0,
    num_services_ok: 0,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=host-1',
    num_relations: 0,
    ...overrides
  }
}

function makeHostOverview(overrides: Partial<HostOverview> = {}): HostOverview {
  return {
    name: 'host-1',
    alias: 'host 1',
    address: '10.0.0.1',
    state: 'UP',
    is_flapping: false,
    stale: false,
    site_id: 'local',
    site_alias: 'Local site',
    folder: '',
    customer: null,
    contact_groups: [],
    tags: {},
    labels: {},
    modes: [],
    service_counts: { ok: 0, warn: 0, crit: 0, unknown: 0, pending: 0, total: 0 },
    last_check: 0,
    last_state_change: 0,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=host-1',
    relations: [],
    more_relations: false,
    ...overrides
  }
}

function makeAction(
  id: string,
  perform: MonitoringAction['perform'],
  withForm = false
): MonitoringAction {
  return {
    id,
    title: untranslated(id),
    submitLabel: untranslated('Submit'),
    ...(withForm && { form: STUB_FORM }),
    defaultValues: () => ({}),
    perform
  }
}

function makeRegistry(perform: MonitoringAction['perform']): MonitoringActionRegistry {
  return {
    [RESCHEDULE_ACTION_ID]: makeAction(RESCHEDULE_ACTION_ID, perform),
    [ACK_ACTION_ID]: makeAction(ACK_ACTION_ID, perform, true)
  }
}

const PERMITTED_ACTIONS: CellAction[] = [
  { id: ACK_ACTION_ID, label: untranslated(ACK_LABEL), icon: 'ack' },
  { id: RESCHEDULE_ACTION_ID, label: untranslated(RESCHEDULE_LABEL), icon: 'reload' }
]

function renderSlideIn(
  actions: MonitoringActionRegistry,
  host: HostEntry | null = makeHost(),
  permittedActions: CellAction[] = PERMITTED_ACTIONS
) {
  return render(HostSlideIn, {
    props: {
      host,
      actions,
      permittedActions,
      loadActionMenu: async () => [],
      displayOptions: DISPLAY_OPTIONS
    }
  })
}

function feedbackSettledByHand(): { promise: Promise<ActionFeedback>; resolve: () => void } {
  let resolve: () => void = () => {}
  const promise = new Promise<ActionFeedback>((res) => {
    resolve = () => res(SUCCESS)
  })
  return { promise, resolve }
}

describe('HostSlideIn', () => {
  beforeEach(() => {
    vi.spyOn(client, 'GET').mockResolvedValue({
      data: undefined,
      error: {},
      response: new Response()
    } as never)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('runs the reschedule action straight away, without opening a form', async () => {
    const perform = vi.fn().mockResolvedValue(SUCCESS)
    renderSlideIn(makeRegistry(perform))

    await userEvent.click(await screen.findByRole('button', { name: RESCHEDULE_LABEL }))

    expect(perform).toHaveBeenCalledWith([{ site_id: 'local', name: 'host-1' }], {})
  })

  it('emits performed with the feedback the action returned', async () => {
    const perform = vi.fn().mockResolvedValue(SUCCESS)
    const { emitted } = renderSlideIn(makeRegistry(perform))

    await userEvent.click(await screen.findByRole('button', { name: RESCHEDULE_LABEL }))

    expect(emitted()['performed']).toEqual([[SUCCESS]])
  })

  it('pulses the reschedule button while the action is in flight', async () => {
    const { promise, resolve } = feedbackSettledByHand()
    renderSlideIn(makeRegistry(vi.fn().mockReturnValue(promise)))

    await userEvent.click(await screen.findByRole('button', { name: RESCHEDULE_LABEL }))

    expect(screen.getByRole('button', { name: RESCHEDULE_LABEL })).toHaveClass(RUNNING_CLASS)

    resolve()
    await promise
  })

  it('stops pulsing when the host changes while an action is still in flight', async () => {
    const { promise, resolve } = feedbackSettledByHand()
    const { rerender } = renderSlideIn(makeRegistry(vi.fn().mockReturnValue(promise)))
    await userEvent.click(await screen.findByRole('button', { name: RESCHEDULE_LABEL }))
    expect(screen.getByRole('button', { name: RESCHEDULE_LABEL })).toHaveClass(RUNNING_CLASS)

    await rerender({ host: makeHost({ name: 'host-2' }) })

    expect(screen.getByRole('button', { name: RESCHEDULE_LABEL })).not.toHaveClass(RUNNING_CLASS)

    resolve()
    await promise
  })

  it('refreshes the header mode icons a moment after an action succeeds', async () => {
    vi.useFakeTimers()
    const user = userEvent.setup({ advanceTimers: (ms: number) => vi.advanceTimersByTime(ms) })
    vi.spyOn(client, 'GET')
      .mockResolvedValueOnce({
        data: makeHostOverview({ modes: [] }),
        error: undefined,
        response: new Response()
      } as never)
      .mockResolvedValue({
        data: makeHostOverview({
          modes: [
            {
              icon_name: 'downtime',
              link: 'view.py?view_name=downtimes_of_host&site=local&host=host-1',
              title: 'In scheduled downtime'
            }
          ]
        }),
        error: undefined,
        response: new Response()
      } as never)
    const perform = vi.fn().mockResolvedValue(SUCCESS)
    renderSlideIn(makeRegistry(perform))
    await vi.advanceTimersByTimeAsync(0)
    expect(screen.queryByRole('link', { name: 'In scheduled downtime' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: RESCHEDULE_LABEL }))
    // The core applies external commands like a scheduled downtime asynchronously, so the
    // reload is delayed rather than immediate, giving it a moment to catch up.
    await vi.advanceTimersByTimeAsync(0)
    expect(client.GET).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(ACTION_REFRESH_DELAY_MS)

    expect(screen.getByRole('link', { name: 'In scheduled downtime' })).toBeInTheDocument()
    // Exactly one more request than the initial load: the Overview tab's own reload (driven by
    // reloadToken) already refreshes the header, so the direct call for the header must not
    // repeat it.
    expect(client.GET).toHaveBeenCalledTimes(2)
  })

  it('still refreshes the header when a tab other than Overview is shown', async () => {
    vi.useFakeTimers()
    const user = userEvent.setup({ advanceTimers: (ms: number) => vi.advanceTimersByTime(ms) })
    vi.spyOn(client, 'GET').mockImplementation(async (path) => {
      if (path === '/monitor/hosts/{hostname}/events') {
        return {
          data: {
            events: [],
            meta: {
              limit: 500,
              truncated: false,
              since: 0,
              time_window_days: 8,
              legacy_events_link: 'view.py?view_name=host_events'
            }
          },
          error: undefined,
          response: new Response()
        } as never
      }
      return {
        data: makeHostOverview({
          modes: [
            {
              icon_name: 'downtime',
              link: 'view.py?view_name=downtimes_of_host&site=local&host=host-1',
              title: 'In scheduled downtime'
            }
          ]
        }),
        error: undefined,
        response: new Response()
      } as never
    })

    render(HostSlideIn, {
      props: {
        host: makeHost(),
        actions: makeRegistry(vi.fn().mockResolvedValue(SUCCESS)),
        permittedActions: PERMITTED_ACTIONS,
        loadActionMenu: async () => [],
        activeTabId: 'history',
        displayOptions: DISPLAY_OPTIONS
      }
    })
    await vi.advanceTimersByTimeAsync(0)
    expect(screen.queryByRole('link', { name: 'In scheduled downtime' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: RESCHEDULE_LABEL }))
    await vi.advanceTimersByTimeAsync(ACTION_REFRESH_DELAY_MS)

    expect(screen.getByRole('link', { name: 'In scheduled downtime' })).toBeInTheDocument()
  })

  it('opens the action pane instead of performing for an action with a form', async () => {
    const perform = vi.fn().mockResolvedValue(SUCCESS)
    renderSlideIn(makeRegistry(perform))

    await userEvent.click(await screen.findByRole('button', { name: ACK_LABEL }))

    expect(perform).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /Back to host detail view/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: RESCHEDULE_LABEL })).not.toBeInTheDocument()
  })

  it('shows no action buttons to a user who may run none of them', async () => {
    renderSlideIn(makeRegistry(vi.fn()), makeHost(), [])

    await screen.findByText('Host details')

    expect(screen.queryByRole('button', { name: RESCHEDULE_LABEL })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: ACK_LABEL })).not.toBeInTheDocument()
  })

  it('leaves out a permitted action this page cannot perform', async () => {
    renderSlideIn(makeRegistry(vi.fn()), makeHost(), [
      ...PERMITTED_ACTIONS,
      {
        id: 'send_custom_notification',
        label: untranslated('Send custom notification'),
        icon: 'notifications'
      }
    ])

    await screen.findByRole('button', { name: ACK_LABEL })

    expect(
      screen.queryByRole('button', { name: 'Send custom notification' })
    ).not.toBeInTheDocument()
  })
})
