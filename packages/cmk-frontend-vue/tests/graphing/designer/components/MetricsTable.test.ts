/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type { TitleMacroGroup } from 'cmk-shared-typing/typescript/custom_graph_designer'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { type MockInstance, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import MetricsTable from '@/graphing/designer/components/MetricsTable.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { useValidationMessages } from '@/graphing/designer/composables/useValidationMessages'
import {
  type DesignerItem,
  newConstantDraft,
  newMetricBackendDraft,
  newRrdMetricDraft,
  newRrdQueryDraft,
  newScalarDraft
} from '@/graphing/designer/drafts'
import type { ItemId } from '@/graphing/designer/types'
import { type RowField, type RowIssue, validateDesign } from '@/graphing/designer/validation'

import {
  constantItem,
  filterDefinitions,
  formulaItem,
  metricBackendItem,
  rrdMetricItem
} from '../fixtures'

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

/** Whether the add-source dropdown took the focus while the spy was installed. */
function focusedAddSource(focus: MockInstance): boolean {
  return focus.mock.contexts.includes(screen.getByRole('combobox', { name: 'Add source' }))
}

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
  createServicesAvailable = true,
  { issuesByRow = new Map<ItemId, RowIssue[]>(), resolvedTitles = new Map<ItemId, string>() } = {}
) {
  const store = useGraphItems(PALETTE)
  store.replaceAll(seed)
  const harness = defineComponent({
    setup() {
      useProvideFilterDefinitions({ definitions: filterDefinitions, groups: {} })
      return () =>
        h(MetricsTable, {
          store,
          thresholds: THRESHOLDS,
          metricBackendAvailable,
          createServicesAvailable,
          metricBackendDefaultTitle: '$METRIC_NAME$ - $SERIES_ID$',
          titleMacros: TITLE_MACROS,
          issuesByRow,
          resolvedTitles
        })
    }
  })
  const utils = render(harness)
  return { store, ...utils }
}

test('a table without sources is header and footer only', () => {
  const { container } = renderTable()

  expect(container.querySelector('thead')).toBeInTheDocument()
  expect(container.querySelector('tfoot')).toBeInTheDocument()
  expect(container.querySelector('tbody')).not.toBeInTheDocument()
})

test('the add-source dropdown takes the focus when the table opens without sources', () => {
  const focus = vi.spyOn(window.HTMLElement.prototype, 'focus')
  renderTable()

  expect(focusedAddSource(focus)).toBe(true)
})

test('the add-source dropdown leaves the focus alone when the table opens with sources', () => {
  const focus = vi.spyOn(window.HTMLElement.prototype, 'focus')
  renderTable([rrdMetricItem('A')])

  expect(focusedAddSource(focus)).toBe(false)
})

test('deleting the last source does not pull the focus to the add-source dropdown', async () => {
  const focus = vi.spyOn(window.HTMLElement.prototype, 'focus')
  const { store } = renderTable([rrdMetricItem('A')])
  await fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

  expect(store.items.value).toHaveLength(0)
  expect(focusedAddSource(focus)).toBe(false)
})

test('adding a source appends an auto-expanded draft row', async () => {
  const { store } = renderTable([rrdMetricItem('A')])
  await fireEvent.click(screen.getByRole('combobox', { name: 'Add source' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Checkmk RRD' }))

  expect(store.items.value.map((item) => item.id)).toEqual(['A', 'B'])
  expect(store.items.value[1]).toMatchObject({ type: 'rrd_metric', host_name: null })
  // The new row opens expanded, showing its source configuration form.
  expect(await screen.findByText('Single selection')).toBeInTheDocument()
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
  expect(await screen.findByRole('spinbutton', { name: /^Constant at/ })).toBeInTheDocument()
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
  expect(screen.getByText('Selected rows: 1')).toBeInTheDocument()

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

test('a row reusing the id of a selected row is not selected itself', async () => {
  const { store } = renderTable([rrdMetricItem('A'), constantItem('B')])
  const selects = () => screen.getAllByLabelText('Select row')
  await fireEvent.click(selects()[1]!)
  expect(screen.getByText('Selected rows: 1')).toBeInTheDocument()

  store.remove('B')
  await waitFor(() => expect(selects()).toHaveLength(1))
  store.addItem((id) => constantItem(id))
  await waitFor(() => expect(selects()).toHaveLength(2))

  expect(screen.queryByText('Selected rows: 1')).not.toBeInTheDocument()
  expect(selects()[1]!).not.toBeChecked()
})

test('title edits patch the row', async () => {
  const { store } = renderTable([rrdMetricItem('A')])
  await fireEvent.update(screen.getByLabelText('Title'), 'My title')
  expect(store.items.value[0]!.title).toBe('My title')
})

test('the display name states what a row resolved to, next to its editable title', () => {
  renderTable([rrdMetricItem('A', { title: '$DEFAULT_TITLE$' })], true, true, {
    resolvedTitles: new Map([['A', 'CPU utilization']])
  })

  expect(screen.getByText('CPU utilization')).toBeInTheDocument()
  expect(screen.getByLabelText('Title')).toHaveValue('$DEFAULT_TITLE$')
})

test('the display name falls back to the stored title of an unresolved row', () => {
  renderTable([rrdMetricItem('A', { title: 'Raw title' })])

  expect(screen.getByText('Raw title')).toBeInTheDocument()
})

test('a formula row expands to the read-only formula form', async () => {
  renderTable([formulaItem('A', { ast: { op: 'num', value: 5 } })])
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle details' }))
  expect(await screen.findByText(/= 5/)).toBeInTheDocument()
})

test('a metric_backend row expands to the metric backend form', async () => {
  renderTable([metricBackendItem('A')])
  await fireEvent.click(screen.getByRole('button', { name: 'Toggle details' }))
  expect(await screen.findByText('Then consolidate by')).toBeInTheDocument()
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
  expect(await screen.findByText('Then consolidate by')).toBeInTheDocument()
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

describe('a blocked row', () => {
  const BLOCKED_ROWS: Record<string, DesignerItem> = {
    'Checkmk RRD': { ...newRrdMetricDraft('A', '#28a2f3'), title: '' },
    'Constant line': { ...newConstantDraft('A', '#28a2f3'), title: '' },
    'Service reference line': { ...newScalarDraft('A', '#28a2f3'), title: '' },
    'Metrics backend': {
      ...newMetricBackendDraft('A'),
      title: '',
      consolidation_function: { type: 'gauge_last', lookback_seconds: 0 }
    },
    'Calculated metric': formulaItem('A', { title: '', ast: { op: 'ref', id: 'Z' } }),
    'Checkmk RRD query': { ...newRrdQueryDraft('A'), title: '' }
  }

  function messagesOf(issues: readonly RowIssue[]): string[] {
    let messages!: string[]
    render(
      defineComponent({
        setup() {
          const { issueMessage } = useValidationMessages()
          messages = issues.map(issueMessage)
          return () => null
        }
      })
    )
    return messages
  }

  function tally(messages: string[]): Map<string, number> {
    const counts = new Map<string, number>()
    for (const message of messages) {
      counts.set(message, (counts.get(message) ?? 0) + 1)
    }
    return counts
  }

  test.each(Object.entries(BLOCKED_ROWS))(
    '%s states each blocker on the field it belongs to',
    async (_kind, row) => {
      const issues = validateDesign([row], filterDefinitions)
      const expected = tally(messagesOf(issues))
      renderTable([row], true, true, { issuesByRow: new Map([[row.id, issues]]) })

      await fireEvent.click(screen.getByRole('button', { name: 'Toggle details' }))

      expect(expected.size).toBeGreaterThan(0)
      for (const [message, count] of expected) {
        expect(await screen.findAllByText(message)).toHaveLength(count)
      }
    }
  )

  test('is marked beside its title, not in the id column', () => {
    const row = newRrdMetricDraft('A', '#28a2f3')
    const issues = validateDesign([row], filterDefinitions)
    renderTable([row], true, true, { issuesByRow: new Map([[row.id, issues]]) })

    const marker = screen.getByLabelText('Source A prevents saving')

    expect(marker.closest('td')).toContainElement(screen.getByRole('textbox', { name: 'Title' }))
  })

  test('the rows above block on every field there is', () => {
    const issues = Object.values(BLOCKED_ROWS).flatMap((row) =>
      validateDesign([row], filterDefinitions)
    )
    const allFields: Record<RowField, true> = {
      title: true,
      host_name: true,
      service_name: true,
      metric_name: true,
      host_filter: true,
      service_filter: true,
      value: true,
      consolidation_function: true,
      ast: true
    }
    expect(new Set(issues.map((issue) => issue.field))).toEqual(new Set(Object.keys(allFields)))
  })
})

test('three metrics are three rows, and deleting one drops only that row', async () => {
  const { store } = renderTable([
    rrdMetricItem('A', { title: 'First' }),
    rrdMetricItem('B', { title: 'Second' }),
    rrdMetricItem('C', { title: 'Third' })
  ])
  expect(screen.getAllByLabelText('Select row')).toHaveLength(3)

  const [, deleteSecond] = screen.getAllByRole('button', { name: 'Delete' })
  await fireEvent.click(deleteSecond!)

  expect(store.items.value.map((item) => item.id)).toEqual(['A', 'C'])
  expect(screen.getAllByLabelText('Select row')).toHaveLength(2)
})
