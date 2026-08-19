/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import { Response } from 'cmk-ui-library/components/CmkSuggestions'
import { expect, test, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import MetricBackendForm from '@/graphing/designer/components/forms/MetricBackendForm.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { type DraftMetricBackendItem, newMetricBackendDraft } from '@/graphing/designer/drafts'

const mocks = vi.hoisted(() => ({ fetchSuggestions: vi.fn(), fetchRestAPIDeprecated: vi.fn() }))

vi.mock(
  import('cmk-ui-library/components/FormAutocompleter/autocompleter'),
  async (importOriginal) => {
    const mod = await importOriginal()
    return { ...mod, fetchSuggestions: mocks.fetchSuggestions }
  }
)

vi.mock(import('cmk-ui-library/lib/cmkFetch'), async (importOriginal) => {
  const mod = await importOriginal()
  return { ...mod, fetchRestAPIDeprecated: mocks.fetchRestAPIDeprecated }
})

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']

function renderForm(seed: DraftMetricBackendItem) {
  mocks.fetchSuggestions.mockResolvedValue(new Response([]))
  mocks.fetchRestAPIDeprecated.mockResolvedValue({
    raiseForStatus: async () => {},
    json: async () => ({ choices: [] })
  })
  const store = useGraphItems(PALETTE)
  store.replaceAll([seed])
  const harness = defineComponent({
    setup() {
      return () => {
        const item = store.items.value.find((candidate) => candidate.id === seed.id)
        return item?.type === 'metric_backend'
          ? h(MetricBackendForm, {
              item,
              store,
              metricNameErrors: [],
              consolidationErrors: []
            })
          : null
      }
    }
  })
  render(harness)
  return store
}

test('composes the metric, attributes and consolidation sections', async () => {
  renderForm(newMetricBackendDraft('A'))

  expect(await screen.findByText('Metric')).toBeInTheDocument()
  expect(screen.getByText('Attributes')).toBeInTheDocument()
  expect(screen.getByText('Consolidation')).toBeInTheDocument()
})

const SUM_BY_SERVICE: Aggregator = {
  stages: [
    {
      aggregate_by: [{ kind: 'resource', name: 'service.name' }],
      aggregation_fn: { type: 'scalar', name: 'sum' }
    }
  ]
}

function storedItem(store: ReturnType<typeof renderForm>): DraftMetricBackendItem {
  const item = store.items.value.find((candidate) => candidate.id === 'A')
  if (item?.type !== 'metric_backend') {
    throw new Error('metric-backend item went missing')
  }
  return item
}

async function openGroupByFunctionDropdown(): Promise<void> {
  await userEvent.click(await screen.findByRole('button', { name: /Edit group by/ }))
  await userEvent.click(screen.getByRole('combobox', { name: 'Grouping function' }))
}

test('a float consolidation offers the float grouping functions, not the histogram ones', async () => {
  renderForm(newMetricBackendDraft('A')) // defaults to the float gauge_last consolidation
  // Editing an empty grouping opens the function dropdown directly.
  await userEvent.click(await screen.findByRole('button', { name: /Edit group by/ }))

  expect(await screen.findByRole('option', { name: 'avg by' })).toBeVisible()
  expect(screen.getByRole('option', { name: 'count by' })).toBeVisible()
  expect(screen.queryByRole('option', { name: 'percentile by' })).toBeNull()
})

test('a stored aggregator populates the group-by widget', async () => {
  renderForm({ ...newMetricBackendDraft('A'), aggregator: SUM_BY_SERVICE })

  const chip = await screen.findByRole('button', { name: /Edit group by/ })
  expect(chip).toHaveTextContent('sum by')
  expect(within(chip).getByText('service.name')).toBeVisible()
})

const MAX_BY_SERVICE: Aggregator = {
  stages: [
    {
      aggregate_by: [{ kind: 'resource', name: 'service.name' }],
      aggregation_fn: { type: 'scalar', name: 'max' }
    }
  ]
}

test('selecting another function re-persists the sibling aggregator', async () => {
  const store = renderForm({ ...newMetricBackendDraft('A'), aggregator: SUM_BY_SERVICE })
  await openGroupByFunctionDropdown()

  await userEvent.click(await screen.findByRole('option', { name: 'max by' }))

  await waitFor(() => expect(storedItem(store).aggregator).toEqual(MAX_BY_SERVICE))
})

test('selecting "no grouping" clears the sibling aggregator', async () => {
  const store = renderForm({ ...newMetricBackendDraft('A'), aggregator: SUM_BY_SERVICE })
  await openGroupByFunctionDropdown()

  await userEvent.click(await screen.findByRole('option', { name: 'no grouping' }))

  await waitFor(() => expect(storedItem(store).aggregator).toBeUndefined())
})

test('adding a then step persists a second aggregator stage', async () => {
  const store = renderForm({ ...newMetricBackendDraft('A'), aggregator: SUM_BY_SERVICE })

  await userEvent.click(await screen.findByRole('button', { name: 'Add then step' }))

  await waitFor(() =>
    expect(storedItem(store).aggregator).toEqual<Aggregator>({
      stages: [
        SUM_BY_SERVICE.stages[0]!,
        // The fresh then step defaults to "avg by everything": an empty aggregate_by.
        { aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'avg' } }
      ]
    })
  )
})

const PRESERVE_QUANTILE_BY_SERVICE: DraftMetricBackendItem['consolidation_function'] = {
  type: 'histogram_preserve_quantile',
  lookback_seconds: 300,
  percentile: 95,
  group_by: [{ kind: 'resource', key: 'service.name' }]
}

test('adding a then step to a histogram grouping persists a then-only aggregator', async () => {
  const store = renderForm({
    ...newMetricBackendDraft('A'),
    consolidation_function: PRESERVE_QUANTILE_BY_SERVICE
  })

  await userEvent.click(await screen.findByRole('button', { name: 'Add then step' }))

  await waitFor(() =>
    expect(storedItem(store).aggregator).toEqual<Aggregator>({
      stages: [{ aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'avg' } }]
    })
  )
  expect(storedItem(store).consolidation_function).toEqual(PRESERVE_QUANTILE_BY_SERVICE)
})

test('a histogram grouping loads its then steps from every aggregator stage', async () => {
  renderForm({
    ...newMetricBackendDraft('A'),
    consolidation_function: PRESERVE_QUANTILE_BY_SERVICE,
    aggregator: SUM_BY_SERVICE
  })

  const chip = await screen.findByRole('button', { name: /Edit then step/ })
  expect(chip).toHaveTextContent('sum by')
})
