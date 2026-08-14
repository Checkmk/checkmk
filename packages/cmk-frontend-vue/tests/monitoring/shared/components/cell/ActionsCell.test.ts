/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import ActionsCell, { type CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

beforeAll(() => {
  // reka-ui's menu interactions rely on pointer-capture APIs that jsdom does not implement.
  window.HTMLElement.prototype.hasPointerCapture = () => false
  window.HTMLElement.prototype.setPointerCapture = () => {}
  window.HTMLElement.prototype.releasePointerCapture = () => {}
})

const ACTIONS: CellAction[] = [
  { id: 'reschedule', label: 'Reschedule check' as TranslatedString, icon: 'reload' },
  { id: 'acknowledge', label: 'Acknowledge' as TranslatedString, icon: 'acknowledge-test' },
  { id: 'downtime', label: 'Schedule downtime' as TranslatedString, icon: 'downtime' }
]

const LOADED: CellAction[] = [
  {
    id: 'inventory',
    label: 'Show HW/SW inventory tree' as TranslatedString,
    icon: 'inventory',
    url: 'view.py?view_name=inv_host&host=web-server-01'
  },
  { id: 'reschedule-cmd', label: 'Reschedule active checks' as TranslatedString, icon: 'reload' }
]

function mountCell(props: {
  actions: CellAction[]
  maxVisible?: number
  load?: () => Promise<CellAction[]>
}) {
  return render(ActionsCell, { props })
}

test('renders only the first maxVisible actions directly plus a "show more" trigger', () => {
  mountCell({ actions: ACTIONS, maxVisible: 2 })

  expect(screen.getByRole('button', { name: 'Reschedule check' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Acknowledge' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Schedule downtime' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'More actions' })).toBeInTheDocument()
})

test('omits the "show more" trigger when all actions fit', () => {
  mountCell({ actions: ACTIONS, maxVisible: 3 })

  expect(screen.queryByRole('button', { name: 'More actions' })).not.toBeInTheDocument()
})

test('emits select with the action when a visible button is clicked', async () => {
  const { emitted } = mountCell({ actions: ACTIONS, maxVisible: 2 })

  await userEvent.click(screen.getByRole('button', { name: 'Reschedule check' }))

  const selectEvents = emitted('select')
  expect(selectEvents).toHaveLength(1)
  expect(selectEvents![0]).toEqual([ACTIONS[0]])
})

test('does not emit select for a disabled action', async () => {
  const actions: CellAction[] = [
    {
      id: 'reschedule',
      label: 'Reschedule check' as TranslatedString,
      icon: 'reload',
      disabled: true
    }
  ]
  const { emitted } = mountCell({ actions, maxVisible: 2 })

  await userEvent.click(screen.getByRole('button', { name: 'Reschedule check' }))

  expect(emitted('select')).toBeUndefined()
})

test('renders an inline action with a url as a native link', () => {
  mountCell({
    actions: [
      {
        id: 'edit',
        label: 'Edit host' as TranslatedString,
        icon: 'edit',
        url: 'wato.py?mode=edit_host&host=web-server-01'
      }
    ],
    maxVisible: 2
  })

  expect(screen.getByRole('link', { name: 'Edit host' })).toHaveAttribute(
    'href',
    'wato.py?mode=edit_host&host=web-server-01'
  )
})

test('a linking action is drawn as the button a commanding one is', () => {
  mountCell({
    actions: [
      { id: 'reschedule', label: 'Reschedule check' as TranslatedString, icon: 'reload' },
      {
        id: 'edit',
        label: 'Edit host' as TranslatedString,
        icon: 'edit',
        url: 'wato.py?mode=edit_host&host=web-server-01'
      }
    ],
    maxVisible: 2
  })

  const command = screen.getByRole('button', { name: 'Reschedule check' })
  const link = screen.getByRole('link', { name: 'Edit host' })
  expect(link.className).toBe(command.className)
  expect(link).toHaveAttribute('target', '_top')
})

test('a linking action navigates rather than emitting a command', async () => {
  const { emitted } = mountCell({
    actions: [
      {
        id: 'edit',
        label: 'Edit host' as TranslatedString,
        icon: 'edit',
        url: 'wato.py?mode=edit_host&host=web-server-01'
      }
    ],
    maxVisible: 2
  })

  await userEvent.click(screen.getByRole('link', { name: 'Edit host' }))

  expect(emitted('select')).toBeUndefined()
})

test('shows the menu trigger when only a lazy loader is provided', () => {
  const load = vi.fn(async () => LOADED)
  mountCell({ actions: [], load })

  expect(screen.getByRole('button', { name: 'More actions' })).toBeInTheDocument()
  expect(load).not.toHaveBeenCalled()
})

test('lazily loads overflow entries on open, rendering links as anchors and commands as buttons', async () => {
  const load = vi.fn(async () => LOADED)
  const { emitted } = mountCell({ actions: [], load })

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))

  const inventory = await screen.findByRole('menuitem', { name: /Show HW\/SW inventory tree/ })
  expect(inventory).toHaveAttribute('href', 'view.py?view_name=inv_host&host=web-server-01')
  expect(load).toHaveBeenCalledTimes(1)

  await userEvent.click(screen.getByRole('menuitem', { name: /Reschedule active checks/ }))
  expect(emitted('select')![0]).toEqual([LOADED[1]])
})

test('shows an empty state when the loader returns nothing', async () => {
  mountCell({ actions: [], load: async () => [] })

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))

  expect(await screen.findByText('No actions available')).toBeInTheDocument()
})

test('shows an error state when loading fails', async () => {
  mountCell({
    actions: [],
    load: async () => {
      throw new Error('boom')
    }
  })

  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))

  expect(await screen.findByText('Could not load actions.')).toBeInTheDocument()
})

test('refetches the loader every time the menu is opened', async () => {
  const load = vi.fn(async () => LOADED)
  mountCell({ actions: [], load })

  const trigger = screen.getByRole('button', { name: 'More actions' })
  await userEvent.click(trigger)
  await screen.findByRole('menuitem', { name: /Show HW\/SW inventory tree/ })
  await userEvent.keyboard('{Escape}')
  await userEvent.click(trigger)

  await waitFor(() => expect(load).toHaveBeenCalledTimes(2))
})
