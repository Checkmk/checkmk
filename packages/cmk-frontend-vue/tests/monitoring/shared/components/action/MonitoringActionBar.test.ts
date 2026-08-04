/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import MonitoringActionBar from '@/monitoring/shared/components/action/MonitoringActionBar.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

const ACTIONS: CellAction[] = [
  { id: 'reschedule', label: 'Reschedule check' as TranslatedString, icon: 'reload' },
  { id: 'acknowledge', label: 'Acknowledge' as TranslatedString, icon: 'acknowledge-test' }
]

function mountBar(props: {
  selectedCount: number
  actions?: CellAction[]
  runningActionId?: string | null
}) {
  return render(MonitoringActionBar, {
    props: {
      actions: ACTIONS,
      selectionLabel: `${props.selectedCount} hosts selected` as TranslatedString,
      label: 'Actions for selected hosts' as TranslatedString,
      ...props
    }
  })
}

const RUNNING_CLASS = 'cmk-button--running'

test('the action performing right away pulses, the others do not', () => {
  mountBar({ selectedCount: 1, runningActionId: 'reschedule' })

  expect(screen.getByRole('button', { name: 'Reschedule check' })).toHaveClass(RUNNING_CLASS)
  expect(screen.getByRole('button', { name: 'Acknowledge' })).not.toHaveClass(RUNNING_CLASS)
})

test('no button pulses while nothing is running', () => {
  mountBar({ selectedCount: 1 })

  expect(screen.getByRole('button', { name: 'Reschedule check' })).not.toHaveClass(RUNNING_CLASS)
})

test('shows the selection label it was given', () => {
  mountBar({ selectedCount: 3 })

  expect(screen.getByText('3 hosts selected')).toBeInTheDocument()
})

test('names the toolbar with the label it was given', () => {
  mountBar({ selectedCount: 3 })

  expect(screen.getByRole('toolbar', { name: 'Actions for selected hosts' })).toBeInTheDocument()
})

test('is enabled and its actions clickable when hosts are selected', async () => {
  const { emitted } = mountBar({ selectedCount: 2 })

  const toolbar = screen.getByRole('toolbar')
  expect(toolbar).toHaveAttribute('aria-disabled', 'false')

  await userEvent.click(screen.getByRole('button', { name: 'Reschedule check' }))

  const actionEvents = emitted('action')
  expect(actionEvents).toHaveLength(1)
  expect(actionEvents![0]).toEqual([ACTIONS[0]])
})

test('is disabled and emits nothing when no hosts are selected', async () => {
  const { emitted } = mountBar({ selectedCount: 0 })

  const toolbar = screen.getByRole('toolbar')
  expect(toolbar).toHaveAttribute('aria-disabled', 'true')

  await userEvent.click(screen.getByRole('button', { name: 'Reschedule check' }))

  expect(emitted('action')).toBeUndefined()
})

test('does not emit for a disabled action even when hosts are selected', async () => {
  const actions: CellAction[] = [
    {
      id: 'reschedule',
      label: 'Reschedule check' as TranslatedString,
      icon: 'reload',
      disabled: true
    }
  ]
  const { emitted } = mountBar({ selectedCount: 2, actions })

  await userEvent.click(screen.getByRole('button', { name: 'Reschedule check' }))

  expect(emitted('action')).toBeUndefined()
})
