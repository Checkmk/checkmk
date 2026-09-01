/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'

import RrdTab from '@/graphing/designer/calculation/components/RrdTab.vue'
import { DEFAULT_TITLE_MACRO, type GraphItem } from '@/graphing/designer/types'

import { formulaItem, items, rrdQueryItem } from '../../fixtures'

const NEXT_ID = 'F'
const NEXT_COLOR = '#ffd703'

function renderTab(tabItems: GraphItem[] = items) {
  return render(RrdTab, { props: { items: tabItems, nextId: NEXT_ID, nextColor: NEXT_COLOR } })
}

function formulaInput(): HTMLInputElement {
  return screen.getByLabelText('Formula input')
}

function colorPicker(): HTMLInputElement {
  return screen.getByLabelText('Formula color')
}

test('adds a committed formula and clears the input', async () => {
  const { emitted } = renderTab()
  await fireEvent.update(formulaInput(), 'A + B')
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & add' }))
  expect(emitted('add')).toEqual([
    [
      {
        type: 'rrd_formula',
        title: DEFAULT_TITLE_MACRO,
        color: NEXT_COLOR,
        ast: {
          op: 'sum',
          operands: [
            { op: 'ref', id: 'A' },
            { op: 'ref', id: 'B' }
          ]
        }
      },
      null
    ]
  ])
  expect(formulaInput().value).toBe('')
})

test('a custom title is committed with the draft', async () => {
  const { emitted } = renderTab()
  await fireEvent.update(screen.getByPlaceholderText('Default title'), 'My calculation')
  await fireEvent.update(formulaInput(), 'A')
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & add' }))
  const [draft] = emitted('add')![0] as [{ title: string }]
  expect(draft.title).toBe('My calculation')
})

test('the hide checkbox marks the used refs as hidden', async () => {
  const { emitted } = renderTab()
  await fireEvent.update(formulaInput(), 'A + B')
  await fireEvent.click(screen.getByLabelText('Hide source metrics from graph'))
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & add' }))
  const [, refVisibility] = emitted('add')![0] as [unknown, unknown]
  expect(refVisibility).toEqual({ ids: ['A', 'B'], visible: false })
})

test('an invalid formula shows its error and emits nothing', async () => {
  const { emitted } = renderTab()
  await fireEvent.update(formulaInput(), 'A +')
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & add' }))
  expect(emitted('add')).toBeUndefined()
  expect(screen.getByText(/End the formula with a metric ID/)).toBeInTheDocument()
})

test('the calculate button stays enabled and reports an empty formula', async () => {
  const { emitted } = renderTab()
  const calculate = screen.getByRole('button', { name: 'Calculate & add' })
  expect(calculate).toBeEnabled()
  await fireEvent.click(calculate)
  expect(emitted('add')).toBeUndefined()
  expect(screen.getByText(/formula is empty/)).toBeInTheDocument()
})

test('submitting an empty formula with Enter shows the empty error', async () => {
  const { emitted } = renderTab()
  await fireEvent.keyUp(formulaInput(), { key: 'Enter' })
  expect(emitted('add')).toBeUndefined()
  expect(screen.getByText(/formula is empty/)).toBeInTheDocument()
})

test('clicking an item badge inserts its id into the formula', async () => {
  renderTab()
  await fireEvent.click(screen.getByRole('button', { name: 'Insert A into the formula' }))
  expect(formulaInput().value).toBe('A')
})

test('switching modes discards the formula input', async () => {
  renderTab()
  await fireEvent.update(formulaInput(), 'A + B')
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle Transformation' }))
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle Operations' }))
  expect(formulaInput().value).toBe('')
})

test('the calculate button stays enabled and reports an incomplete transformation', async () => {
  const { emitted } = renderTab()
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle Transformation' }))
  const calculate = screen.getByRole('button', { name: 'Calculate & add' })
  expect(calculate).toBeEnabled()
  await fireEvent.click(calculate)
  expect(emitted('add')).toBeUndefined()
  expect(screen.getByText('Select the metric to transform.')).toBeInTheDocument()
  expect(screen.getByText('Enter a percentile between 0 and 100.')).toBeInTheDocument()
})

test('in transformation mode a badge click selects the metric', async () => {
  const user = userEvent.setup()
  const { emitted } = renderTab()
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle Transformation' }))
  await fireEvent.click(screen.getByRole('button', { name: 'Select A for the transformation' }))
  await user.click(screen.getByRole('combobox', { name: 'Transformation' }))
  await user.click(await screen.findByRole('option', { name: '95' }))
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & add' }))
  expect(emitted('add')).toEqual([
    [
      {
        type: 'rrd_formula',
        title: DEFAULT_TITLE_MACRO,
        color: NEXT_COLOR,
        ast: { op: 'percentile', percentile: 95, operand: { op: 'ref', id: 'A' } }
      },
      null
    ]
  ])
})

test('a query says why it cannot be transformed, in the list and in the dropdown', async () => {
  const user = userEvent.setup()
  renderTab([rrdQueryItem('A')])
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle Transformation' }))

  expect(screen.getByRole('button', { name: 'Select A for the transformation' })).toHaveAttribute(
    'title',
    'A percentile needs one metric. This query selects several. Aggregate it in a calculation first.'
  )

  const metric = screen.getByRole('combobox', { name: 'Metric' })
  await user.click(metric)
  expect(
    await screen.findByText(
      'A percentile needs one metric. Add a single metric, or aggregate a query in a calculation first.'
    )
  ).toBeInTheDocument()
  expect(metric).toHaveTextContent('No metric available')
})

test('editing a formula seeds the operations editor and commits an update', async () => {
  const { emitted } = renderTab()
  await fireEvent.click(screen.getByRole('button', { name: 'Edit D' }))
  expect(formulaInput().value).toBe('A')
  await fireEvent.update(formulaInput(), 'A + B')
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & update' }))
  expect(emitted('add')).toBeUndefined()
  expect(emitted('update')).toEqual([
    [
      'D',
      {
        type: 'rrd_formula',
        title: DEFAULT_TITLE_MACRO,
        color: '#28a2f3',
        ast: {
          op: 'sum',
          operands: [
            { op: 'ref', id: 'A' },
            { op: 'ref', id: 'B' }
          ]
        }
      },
      { ids: ['A', 'B'], visible: true }
    ]
  ])
  expect(screen.getByText('Calculation updated')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Calculate & add' })).toBeInTheDocument()
})

test('editing a percentile jumps to the transformation mode', async () => {
  const percentileItem = formulaItem('P', {
    ast: { op: 'percentile', percentile: 90, operand: { op: 'ref', id: 'A' } }
  })
  const { emitted } = renderTab([...items, percentileItem])
  await fireEvent.click(screen.getByRole('button', { name: 'Edit P' }))
  expect(screen.queryByLabelText('Formula input')).not.toBeInTheDocument()
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & update' }))
  expect(emitted('update')).toEqual([
    [
      'P',
      {
        type: 'rrd_formula',
        title: DEFAULT_TITLE_MACRO,
        color: '#28a2f3',
        ast: { op: 'percentile', percentile: 90, operand: { op: 'ref', id: 'A' } }
      },
      { ids: ['A'], visible: true }
    ]
  ])
})

test('previews the next id and color while adding', () => {
  renderTab()
  expect(colorPicker().value).toBe(NEXT_COLOR)
  expect(screen.getByText(NEXT_ID)).toBeInTheDocument()
})

test('editing shows the item id and color and commits a changed color', async () => {
  const { emitted } = renderTab()
  await fireEvent.click(screen.getByRole('button', { name: 'Edit D' }))
  expect(colorPicker().value).toBe('#28a2f3')

  await fireEvent.update(colorPicker(), '#ff8400')
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & update' }))
  const [, draft] = emitted('update')![0] as [unknown, { color: string }]
  expect(draft.color).toBe('#ff8400')

  expect(colorPicker().value).toBe(NEXT_COLOR)
})

test('the delete action emits the delete event', async () => {
  const { emitted } = renderTab()
  await fireEvent.click(screen.getByRole('button', { name: 'Delete D' }))
  expect(emitted('delete')).toEqual([['D']])
})

test('a newly added item gets the success alert once it appears', async () => {
  const { emitted, rerender } = renderTab()
  await fireEvent.update(formulaInput(), 'A')
  await fireEvent.click(screen.getByRole('button', { name: 'Calculate & add' }))
  expect(emitted('add')).toHaveLength(1)
  expect(screen.queryByText('Calculation added')).not.toBeInTheDocument()

  await rerender({ items: [...items, formulaItem('F', { ast: { op: 'ref', id: 'A' } })] })
  expect(screen.getByText('Calculation added')).toBeInTheDocument()
})

test('while editing, dynamic and cycle-back rows say why they block', async () => {
  const dependent = formulaItem('F', { ast: { op: 'ref', id: 'D' } })
  renderTab([...items, dependent])
  await fireEvent.click(screen.getByRole('button', { name: 'Edit D' }))
  expect(screen.getByRole('button', { name: 'Insert D into the formula' })).toHaveAttribute(
    'title',
    'This calculation is currently being edited.'
  )
  expect(screen.getByRole('button', { name: 'Insert F into the formula' })).toHaveAttribute(
    'title',
    'This calculation refers to the one being edited. A reference back would create a cycle.'
  )
  expect(screen.getByRole('button', { name: 'Insert A into the formula' })).toBeEnabled()
})

test('renders the Calculations and Source metrics sections', () => {
  renderTab()
  expect(screen.getByRole('region', { name: 'Calculations' })).toBeInTheDocument()
  expect(screen.getByRole('region', { name: 'Source metrics' })).toBeInTheDocument()
})
