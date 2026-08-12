/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { expect, test } from 'vitest'

import FormulaForm from '@/graphing/designer/components/forms/FormulaForm.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import type { DesignerItem } from '@/graphing/designer/drafts'

import { formulaItem, parseOrThrow, rrdMetricItem } from '../fixtures'

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']

/** Seeds the store and renders the formula row 'F' off it. */
function renderFormulaForm(seed: DesignerItem[]) {
  const store = useGraphItems(PALETTE)
  store.replaceAll(seed)
  const item = store.items.value.find((candidate) => candidate.id === 'F')
  if (item?.type !== 'rrd_formula') {
    throw new Error(`expected an rrd_formula row, got ${item?.type}`)
  }
  render(FormulaForm, { props: { item, store } })
  return store
}

test('lists the direct refs as id + description, toggled by the formula display value', async () => {
  renderFormulaForm([
    rrdMetricItem('A'),
    rrdMetricItem('B', { host_name: 'h2', service_name: 's2', metric_name: 'm2' }),
    formulaItem('F', { ast: parseOrThrow('A + B') })
  ])

  const trigger = screen.getByRole('button', { name: /= A \+ B/ })
  expect(trigger).toHaveAttribute('aria-expanded', 'false')

  await fireEvent.click(trigger)
  expect(trigger).toHaveAttribute('aria-expanded', 'true')

  expect(screen.getByText('my-host > CPU utilization > util')).toBeInTheDocument()
  expect(screen.getByText('h2 > s2 > m2')).toBeInTheDocument()
})

test('shows an empty message when the formula references no sources', () => {
  renderFormulaForm([formulaItem('F', { ast: { op: 'num', value: 5 } })])

  expect(screen.getByText('This formula references no sources.')).toBeInTheDocument()
})
