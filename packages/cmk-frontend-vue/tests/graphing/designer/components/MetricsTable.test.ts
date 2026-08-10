/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type { TitleMacroGroup } from 'cmk-shared-typing/typescript/custom_graph_designer'
import { type MockInstance, vi } from 'vitest'

import MetricsTable from '@/graphing/designer/components/MetricsTable.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { type DesignerItem, newMetricBackendDraft } from '@/graphing/designer/drafts'

import { constantItem, formulaItem, metricBackendItem, rrdMetricItem } from '../fixtures'

vi.mock('@/graphing/designer/components/MetricBackendRuleSlideIn.vue', () => ({
  default: {
    props: ['open', 'item', 'defaultTitle'],
    emits: ['close'],
    template: `<div
      data-testid="metric-backend-rule-slidein"
      :data-item-id="item?.id"
      :data-default-title="defaultTitle"
    ></div>`
  }
}))

afterEach(() => {
  vi.restoreAllMocks()
})

const ADD_RULE_LABEL = 'Add rule: Metric backend (Custom query)'

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400', '#ec48b6', '#ffd703']
const THRESHOLDS = { warning: '#ffd000', critical: '#ff3232' }
const TITLE_MACROS: TitleMacroGroup[] = [
  { source_type: 'rrd_metric', macros: ['$DEFAULT_TITLE$', '$METRIC_NAME$'] }
]

/** Waits for the row group holding `id` to have been scrolled into view. */
async function expectScrolledToRow(scrollIntoView: MockInstance, id: string): Promise<void> {
  await waitFor(() => {
    const scrolled = scrollIntoView.mock.contexts.at(-1)
    expect(scrolled).toBeInstanceOf(HTMLElement)
    expect(within(scrolled as HTMLElement).getByText(id)).toBeInTheDocument()
  })
}

function renderTable(
  seed: DesignerItem[] = [],
  metricBackendAvailable = true,
  createServicesAvailable = true
) {
  const store = useGraphItems(PALETTE, seed)
  const utils = render(MetricsTable, {
    props: {
      store,
      thresholds: THRESHOLDS,
      metricBackendAvailable,
      createServicesAvailable,
      metricBackendDefaultTitle: '$METRIC_NAME$ - $SERIES_ID$',
      titleMacros: TITLE_MACROS
    }
  })
  return { store, ...utils }
}

test('adding a source appends an auto-expanded draft row', async () => {
  const { store } = renderTable([rrdMetricItem('A')])
  await fireEvent.click(screen.getByRole('combobox', { name: 'Add source' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Checkmk RRD' }))

  expect(store.items.value.map((item) => item.id)).toEqual(['A', 'B'])
  expect(store.items.value[1]).toMatchObject({ type: 'rrd_metric', host_name: null })
  // The new row opens expanded, showing its source configuration form.
  expect(await screen.findByText('Single metric')).toBeInTheDocument()
})

test('the added row is scrolled into view', async () => {
  const scrollIntoView = vi.spyOn(window.HTMLElement.prototype, 'scrollIntoView')
  renderTable([rrdMetricItem('A')])
  await fireEvent.click(screen.getByRole('combobox', { name: 'Add source' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Checkmk RRD' }))

  await expectScrolledToRow(scrollIntoView, 'B')
})

test('a cloned row is scrolled into view', async () => {
  const scrollIntoView = vi.spyOn(window.HTMLElement.prototype, 'scrollIntoView')
  renderTable([rrdMetricItem('A')])
  await fireEvent.click(screen.getByRole('button', { name: 'Clone' }))

  await expectScrolledToRow(scrollIntoView, 'B')
})

test('adding a constant line opens the constant form', async () => {
  const { store } = renderTable()
  await fireEvent.click(screen.getByRole('combobox', { name: 'Add source' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Constant line' }))

  expect(store.items.value[0]).toMatchObject({ type: 'constant', value: null })
  expect(await screen.findByRole('spinbutton', { name: 'Constant at' })).toBeInTheDocument()
})

test('adding a service reference line opens the scalar form', async () => {
  const { store } = renderTable()
  await fireEvent.click(screen.getByRole('combobox', { name: 'Add source' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Service reference line' }))

  expect(store.items.value[0]).toMatchObject({
    type: 'scalar',
    scalar_type: 'warning',
    color: THRESHOLDS.warning,
    host_name: null
  })
  expect(await screen.findByRole('combobox', { name: 'Threshold type' })).toBeInTheDocument()
})

test('deleting an unreferenced row needs no confirmation', async () => {
  const { store } = renderTable([rrdMetricItem('A')])
  await fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

  expect(store.items.value).toHaveLength(0)
  expect(screen.queryByText('Delete A?')).not.toBeInTheDocument()
})

test('deleting a referenced row asks and cascades to its dependents', async () => {
  const { store } = renderTable([
    rrdMetricItem('A'),
    formulaItem('B', { ast: { op: 'ref', id: 'A' } })
  ])
  const [deleteA] = screen.getAllByRole('button', { name: 'Delete' })
  await fireEvent.click(deleteA!)

  expect(await screen.findByText('Delete A?')).toBeInTheDocument()
  expect(store.items.value).toHaveLength(2)

  await fireEvent.click(screen.getByRole('button', { name: 'Delete all' }))
  expect(store.items.value).toHaveLength(0)
})

test('selecting rows reveals the bulk actions; bulk clone copies and clears the selection', async () => {
  const { store } = renderTable([rrdMetricItem('A'), constantItem('B')])
  expect(screen.queryByRole('button', { name: 'Clone selected sources' })).not.toBeInTheDocument()

  const [selectA] = screen.getAllByLabelText('Select row')
  await fireEvent.click(selectA!)

  await fireEvent.click(screen.getByRole('button', { name: 'Clone selected sources' }))
  expect(store.items.value.map((item) => item.id)).toEqual(['A', 'C', 'B'])
  expect(screen.queryByRole('button', { name: 'Clone selected sources' })).not.toBeInTheDocument()
})

test('bulk delete of a referenced row routes through the confirmation', async () => {
  const { store } = renderTable([
    rrdMetricItem('A'),
    formulaItem('B', { ast: { op: 'ref', id: 'A' } })
  ])
  const [selectA] = screen.getAllByLabelText('Select row')
  await fireEvent.click(selectA!)
  await fireEvent.click(screen.getByRole('button', { name: 'Delete selected sources' }))

  await fireEvent.click(await screen.findByRole('button', { name: 'Delete all' }))
  expect(store.items.value).toHaveLength(0)
})

test('a selected row deleted outside the table drops out of the bulk actions', async () => {
  const { store } = renderTable([rrdMetricItem('A'), constantItem('B')])
  const [selectA] = screen.getAllByLabelText('Select row')
  await fireEvent.click(selectA!)
  expect(screen.getByRole('button', { name: 'Delete selected sources' })).toBeInTheDocument()

  // E.g. deleted through the calculation slideout, which bypasses the table's own flow.
  store.remove('A')
  await waitFor(() => {
    expect(
      screen.queryByRole('button', { name: 'Delete selected sources' })
    ).not.toBeInTheDocument()
  })
})

test('title edits patch the row', async () => {
  const { store } = renderTable([rrdMetricItem('A')])
  await fireEvent.update(screen.getByLabelText('Title'), 'My title')
  expect(store.items.value[0]!.title).toBe('My title')
})

test('a formula row expands to the read-only formula form', async () => {
  renderTable([formulaItem('A', { ast: { op: 'num', value: 5 } })])
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle details' }))
  expect(await screen.findByRole('button', { name: /= 5/ })).toBeInTheDocument()
})

test('a metric_backend row expands to the metric backend form', async () => {
  renderTable([metricBackendItem('A')])
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle details' }))
  expect(await screen.findByText('Consolidation')).toBeInTheDocument()
})

test('the metric backend source is offered only when the feature is available', async () => {
  renderTable([], false)
  await fireEvent.click(screen.getByRole('combobox', { name: 'Add source' }))
  expect(screen.queryByRole('option', { name: 'Metrics backend' })).not.toBeInTheDocument()
})

test('adding a metric backend source opens its form', async () => {
  const { store } = renderTable([], true)
  await fireEvent.click(screen.getByRole('combobox', { name: 'Add source' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Metrics backend' }))

  expect(store.items.value[0]).toMatchObject({ type: 'metric_backend', metric_name: null })
  expect(await screen.findByText('Consolidation')).toBeInTheDocument()
})

test('the title column header exposes the rendered macro help', async () => {
  renderTable([rrdMetricItem('A')])
  await fireEvent.click(screen.getByRole('button', { name: 'Help for Title' }))
  const tooltip = await screen.findByRole('tooltip')
  expect(tooltip).toHaveTextContent('Available title macros:')
  expect(tooltip).toHaveTextContent('Checkmk RRD (single): $DEFAULT_TITLE$, $METRIC_NAME$')
})

test('a complete metric_backend row offers the add-rule action', () => {
  renderTable([metricBackendItem('A')])
  expect(screen.getByRole('button', { name: ADD_RULE_LABEL })).toBeInTheDocument()
})

test('the add-rule action is absent on non metric_backend rows', () => {
  renderTable([rrdMetricItem('A')])
  expect(screen.queryByRole('button', { name: ADD_RULE_LABEL })).not.toBeInTheDocument()
})

test('the add-rule action is absent while the metric_backend query is incomplete', () => {
  renderTable([newMetricBackendDraft('A')])
  expect(screen.queryByRole('button', { name: ADD_RULE_LABEL })).not.toBeInTheDocument()
})

test('the add-rule action is absent when the metric backend is unavailable', () => {
  renderTable([metricBackendItem('A')], false)
  expect(screen.queryByRole('button', { name: ADD_RULE_LABEL })).not.toBeInTheDocument()
})

test('the add-rule action is absent when creating services is unavailable', () => {
  renderTable([metricBackendItem('A')], true, false)
  expect(screen.queryByRole('button', { name: ADD_RULE_LABEL })).not.toBeInTheDocument()
})

test('clicking the add-rule action opens the rule slide-in for that row', async () => {
  renderTable([metricBackendItem('A')])
  expect(screen.queryByTestId('metric-backend-rule-slidein')).not.toBeInTheDocument()

  await fireEvent.click(screen.getByRole('button', { name: ADD_RULE_LABEL }))

  const slideIn = await screen.findByTestId('metric-backend-rule-slidein')
  expect(slideIn).toHaveAttribute('data-item-id', 'A')
  expect(slideIn).toHaveAttribute('data-default-title', '$METRIC_NAME$ - $SERIES_ID$')
})
