/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import DeleteConfirmationPopup from '@/graphing/designer/components/DeleteConfirmationPopup.vue'
import type { PendingDelete } from '@/graphing/designer/composables/useDeleteConfirmation'

import { formulaItem } from '../fixtures'

// The dialog mounts its content on the open transition, so open starts false.
async function renderPopup(pending: Partial<PendingDelete> = {}) {
  const props = {
    open: false,
    pending: {
      targets: [{ id: 'D', name: 'CPU load' }],
      dependents: [],
      all: false,
      ...pending
    }
  }
  const utils = render(DeleteConfirmationPopup, { props })
  await utils.rerender({ ...props, open: true })
  return utils
}

test('names a single row by its name', async () => {
  await renderPopup()
  expect(screen.getByText('Delete metric CPU load?')).toBeInTheDocument()
  expect(screen.getByText('This action can’t be undone.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
})

test('names every row of a bulk deletion', async () => {
  await renderPopup({
    targets: [
      { id: 'A', name: 'CPU load' },
      { id: 'B', name: 'Memory' }
    ]
  })
  expect(screen.getByText('Delete metrics CPU load, Memory?')).toBeInTheDocument()
})

test('a deletion of every row asks to delete all', async () => {
  await renderPopup({ all: true })
  expect(screen.getByText('Delete all metrics?')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Delete all' })).toBeInTheDocument()
})

test('lists the dependents that are deleted as well', async () => {
  await renderPopup({
    dependents: [
      formulaItem('E', { ast: { op: 'ref', id: 'D' } }),
      formulaItem('F', {
        ast: { op: 'percentile', percentile: 95, operand: { op: 'ref', id: 'D' } }
      })
    ]
  })
  expect(
    screen.getByText('Calculations that use this metric are also deleted:')
  ).toBeInTheDocument()
  expect(screen.getByText('E = D')).toBeInTheDocument()
  expect(screen.getByText('F = 95th percentile of D')).toBeInTheDocument()
})

test('confirming emits confirm, cancelling emits close', async () => {
  const { emitted } = await renderPopup()
  await fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
  expect(emitted('confirm')).toHaveLength(1)

  await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(emitted('close')).toHaveLength(1)
})
