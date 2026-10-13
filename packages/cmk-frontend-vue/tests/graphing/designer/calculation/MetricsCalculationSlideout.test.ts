/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'

import MetricsCalculationSlideout from '@/graphing/designer/calculation/MetricsCalculationSlideout.vue'
import type { ItemId } from '@/graphing/designer/types'

import { formulaItem, rrdMetricItem } from '../fixtures'

const items = [
  rrdMetricItem('A'),
  formulaItem('D', { ast: { op: 'ref', id: 'A' } }),
  formulaItem('E', {
    ast: { op: 'percentile', percentile: 95, operand: { op: 'ref', id: 'A' } }
  })
]
const props = { items, nextId: 'B', nextColor: '#ffd703' }

// The slide-in dialog mounts its content on the open transition, so open starts false.
async function renderSlideout(editing: ItemId | null = null) {
  const utils = render(MetricsCalculationSlideout, { props: { open: false, editing, ...props } })
  await utils.rerender({ open: true, editing, ...props })
  return utils
}

test('splits items into calculations and source metrics', async () => {
  await renderSlideout()
  const calculations = within(screen.getByRole('region', { name: 'Calculations' }))
  expect(
    calculations.getByRole('button', { name: 'Insert D into the formula' })
  ).toBeInTheDocument()

  const sources = within(screen.getByRole('region', { name: 'Source metrics' }))
  expect(sources.getByRole('button', { name: 'Insert A into the formula' })).toBeInTheDocument()
  expect(
    sources.queryByRole('button', { name: 'Insert D into the formula' })
  ).not.toBeInTheDocument()
})

test('"Preview in graph" closes the slideout', async () => {
  const { emitted } = await renderSlideout()
  await fireEvent.click(screen.getByRole('button', { name: 'Preview in graph' }))
  expect(emitted('close')).toHaveLength(1)
})

test('passes add commits through with the ref visibility', async () => {
  const { emitted } = await renderSlideout()
  await fireEvent.update(screen.getByLabelText('Formula input'), 'A + D')
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & add' }))
  const [draft, refVisibility] = emitted('add')![0] as [{ type: string; color: string }, unknown]
  expect(draft.type).toBe('rrd_formula')
  expect(draft.color).toBe('#ffd703')
  expect(refVisibility).toBeNull()
})

test('passes the delete event through', async () => {
  const { emitted } = await renderSlideout()
  await fireEvent.click(screen.getByRole('button', { name: 'Delete D' }))
  expect(emitted('delete')).toEqual([['D']])
})

test('opening on a transformation focuses its metric selection', async () => {
  await renderSlideout('E')
  await waitFor(() => expect(screen.getByRole('combobox', { name: 'Metric' })).toHaveFocus())
})
