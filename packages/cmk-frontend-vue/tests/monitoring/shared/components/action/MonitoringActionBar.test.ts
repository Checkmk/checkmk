/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import type { TranslatedString } from '@/lib/i18nString'

import MonitoringActionBar from '@/monitoring/shared/components/action/MonitoringActionBar.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

const ACTIONS: CellAction[] = [
  { id: 'reschedule', label: 'Reschedule check' as TranslatedString, icon: 'reload' },
  { id: 'acknowledge', label: 'Acknowledge' as TranslatedString, icon: 'acknowledge-test' }
]

function mountBar(props: { selectedCount: number; actions?: CellAction[] }) {
  return render(MonitoringActionBar, {
    props: { actions: ACTIONS, ...props }
  })
}

test('shows the selected-host count', () => {
  mountBar({ selectedCount: 3 })

  expect(screen.getByText('3 hosts selected')).toBeInTheDocument()
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
