/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions'
import {
  type FilterDefinitions,
  useProvideFilterDefinitions
} from 'cmk-ui-library/components/filter'
import { expect, test, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import RrdQueryForm from '@/graphing/designer/components/forms/RrdQueryForm.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { type DraftRRDQueryItem, newRrdQueryDraft } from '@/graphing/designer/drafts'

const mocks = vi.hoisted(() => ({ fetchSuggestions: vi.fn() }))

vi.mock(
  import('cmk-ui-library/components/FormAutocompleter/autocompleter'),
  async (importOriginal) => {
    const mod = await importOriginal()
    return { ...mod, fetchSuggestions: mocks.fetchSuggestions }
  }
)

// Stub the filter editor/remove widgets so the test drives the sync logic, not the widgets.
vi.mock(import('cmk-ui-library/components/filter'), async (importOriginal) => {
  const mod = await importOriginal()
  return {
    ...mod,
    CmkFilterInputItem: {
      props: ['filterId', 'configuredFilterValues'],
      emits: ['update-filter-values'],
      template:
        `<button :data-testid="'update-' + filterId"` +
        ` @click="$emit('update-filter-values', filterId, { op: 'is', value: 'x' })">update</button>`
    } as unknown as (typeof mod)['CmkFilterInputItem'],
    CmkRemoveFilterButton: {
      props: ['filterName'],
      emits: ['remove'],
      template: `<button data-testid="remove-btn" @click="$emit('remove')">remove</button>`
    } as unknown as (typeof mod)['CmkRemoveFilterButton']
  }
})

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']

const DEFINITIONS = {
  host_label: {
    id: 'host_label',
    title: 'Host label',
    domainType: 'visual_filter',
    extensions: { info: 'host', group: null, is_show_more: false, components: [] }
  },
  svcstate: {
    id: 'svcstate',
    title: 'Service states',
    domainType: 'visual_filter',
    extensions: { info: 'service', group: null, is_show_more: false, components: [] }
  }
} as unknown as FilterDefinitions

function renderQueryForm(seed: DraftRRDQueryItem) {
  const store = useGraphItems(PALETTE)
  store.replaceAll([seed])
  const harness = defineComponent({
    setup() {
      useProvideFilterDefinitions({ definitions: DEFINITIONS, groups: {} })
      return () => {
        const item = store.items.value.find((candidate) => candidate.id === seed.id)
        return item?.type === 'rrd_query'
          ? h(RrdQueryForm, { item, store, metricNameErrors: [] })
          : null
      }
    }
  })
  render(harness)
  return store
}

/** The single row's context, narrowed to the query shape. */
function contextOf(
  store: ReturnType<typeof useGraphItems>
): Record<string, Record<string, string>> {
  const item = store.items.value[0]
  if (item?.type !== 'rrd_query') {
    throw new Error(`expected an rrd_query row, got ${item?.type}`)
  }
  return item.context
}

test('adding a host filter from the dropdown activates it without changing the context yet', async () => {
  const store = renderQueryForm(newRrdQueryDraft('A'))

  await fireEvent.click(screen.getByRole('combobox', { name: 'Add host filter' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Host label' }))

  expect(await screen.findByTestId('update-host_label')).toBeInTheDocument()
  expect(contextOf(store)).toEqual({})
})

test('updating a filter syncs its values into the query context', async () => {
  const store = renderQueryForm({
    ...newRrdQueryDraft('A'),
    context: { host_label: { existing: 'v' } }
  })

  await fireEvent.click(screen.getByTestId('update-host_label'))

  expect(contextOf(store)).toEqual({ host_label: { op: 'is', value: 'x' } })
})

test('removing a filter clears it from the context', async () => {
  const store = renderQueryForm({
    ...newRrdQueryDraft('A'),
    context: { host_label: { existing: 'v' } }
  })

  await fireEvent.click(screen.getByTestId('remove-btn'))

  expect(contextOf(store)).toEqual({})
})

test('a service filter renders in the service section', async () => {
  renderQueryForm({ ...newRrdQueryDraft('A'), context: { svcstate: { st0: 'on' } } })

  expect(await screen.findByTestId('update-svcstate')).toBeInTheDocument()
})

test('the metric autocompleter resolves suggestions independent of an exact host+service', async () => {
  mocks.fetchSuggestions.mockResolvedValue(new Response([]))
  renderQueryForm({ ...newRrdQueryDraft('A'), context: { host: { host: 'v300' } } })

  await fireEvent.click(await screen.findByTitle('Select service metric'))

  const lastCall = mocks.fetchSuggestions.mock.calls.at(-1)
  expect(lastCall).toBeDefined()
  const [autocompleter] = lastCall!
  expect(autocompleter.data.ident).toBe('monitored_metrics')
  expect(autocompleter.data.params.show_independent_of_context).toBe(true)
})

test('changing the consolidation updates the row', async () => {
  const store = renderQueryForm({ ...newRrdQueryDraft('A'), metric_name: 'util' })

  await fireEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Max' }))

  expect(store.items.value[0]).toMatchObject({ consolidation: 'max' })
})
