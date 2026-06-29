/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import type { TranslatedString } from '@/lib/i18nString'

import ActionsCell, { type CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

const ACTIONS: CellAction[] = [
  { id: 'reschedule', label: 'Reschedule check' as TranslatedString, icon: 'reload' },
  { id: 'acknowledge', label: 'Acknowledge' as TranslatedString, icon: 'acknowledge-test' },
  { id: 'downtime', label: 'Schedule downtime' as TranslatedString, icon: 'downtime' }
]

function mountCell(props: { actions: CellAction[]; maxVisible?: number }) {
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
