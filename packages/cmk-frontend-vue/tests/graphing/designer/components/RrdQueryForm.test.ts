/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { expect, test, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import RrdQueryForm from '@/graphing/designer/components/forms/RrdQueryForm.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { type DraftRRDQueryItem, newRrdQueryDraft } from '@/graphing/designer/drafts'
import { validateRow } from '@/graphing/designer/validation'

import { filterDefinitions } from '../fixtures'

const mocks = vi.hoisted(() => ({ fetchSuggestions: vi.fn() }))

vi.mock(
  import('cmk-ui-library/components/FormAutocompleter/autocompleter'),
  async (importOriginal) => {
    const mod = await importOriginal()
    return { ...mod, fetchSuggestions: mocks.fetchSuggestions }
  }
)

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']

function renderQueryForm(
  seed: DraftRRDQueryItem,
  filterErrors: { host?: TranslatedString[]; service?: TranslatedString[] } = {}
) {
  const store = useGraphItems(PALETTE)
  store.replaceAll([seed])
  const harness = defineComponent({
    setup() {
      useProvideFilterDefinitions({ definitions: filterDefinitions, groups: {} })
      return () => {
        const item = store.items.value.find((candidate) => candidate.id === seed.id)
        return item?.type === 'rrd_query'
          ? h(RrdQueryForm, {
              item,
              store,
              metricNameErrors: [],
              hostFilterErrors: filterErrors.host ?? [],
              serviceFilterErrors: filterErrors.service ?? []
            })
          : null
      }
    }
  })
  render(harness)
  return store
}

/** The section carrying the given add-dropdown, its active filters included. */
function section(addLabel: string): HTMLElement {
  const container = screen
    .getByRole('combobox', { name: addLabel })
    .closest('.graphing-filter-query-section__container')
  if (container === null) {
    throw new Error(`no filter section around "${addLabel}"`)
  }
  return container as HTMLElement
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

test('adding a host filter from the dropdown puts it into the context, still without a value', async () => {
  const store = renderQueryForm(newRrdQueryDraft('A'))

  await fireEvent.click(screen.getByRole('combobox', { name: 'Add host filter' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Host name (regex)' }))

  expect(within(section('Add host filter')).getByRole('textbox')).toBeInTheDocument()
  expect(contextOf(store)).toEqual({ hostregex: { host_regex: '' } })
})

test('the folder filter satisfies its section on the value the widget reports', async () => {
  const store = renderQueryForm(newRrdQueryDraft('A'))

  await fireEvent.click(screen.getByRole('combobox', { name: 'Add host filter' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Folder' }))

  expect(contextOf(store)).toEqual({ wato_folder: { wato_folder: '' } })
  const row = store.items.value[0]!
  expect(validateRow(row, filterDefinitions)).not.toContainEqual(
    expect.objectContaining({ field: 'host_filter' })
  )
})

test('typing into a filter syncs its value into the query context', async () => {
  const store = renderQueryForm({
    ...newRrdQueryDraft('A'),
    context: { hostregex: { host_regex: '' } }
  })

  await fireEvent.update(screen.getByRole('textbox'), 'my-host')

  expect(contextOf(store)).toEqual({ hostregex: { host_regex: 'my-host' } })
})

test('clearing a filter leaves it in the context without a value', async () => {
  const store = renderQueryForm({
    ...newRrdQueryDraft('A'),
    context: { hostregex: { host_regex: 'my-host' } }
  })

  await fireEvent.update(screen.getByRole('textbox'), '')

  expect(contextOf(store)).toEqual({ hostregex: { host_regex: '' } })
})

test('removing a filter clears it from the context', async () => {
  const store = renderQueryForm({
    ...newRrdQueryDraft('A'),
    context: { hostregex: { host_regex: 'my-host' } }
  })

  await fireEvent.click(screen.getByRole('button', { name: 'Remove Host name (regex) filter' }))

  expect(contextOf(store)).toEqual({})
})

test('a service filter renders in the service section', () => {
  renderQueryForm({ ...newRrdQueryDraft('A'), context: { serviceregex: { service_regex: 'CPU' } } })

  expect(
    within(section('Add service filter')).getByRole('button', {
      name: 'Remove Service name (regex) filter'
    })
  ).toBeInTheDocument()
})

test('the metric autocompleter resolves suggestions independent of an exact host+service', async () => {
  mocks.fetchSuggestions.mockResolvedValue(new Response([]))
  renderQueryForm({ ...newRrdQueryDraft('A'), context: { hostregex: { host_regex: 'v300' } } })

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

test('both filter sections ask for a filter', () => {
  renderQueryForm(newRrdQueryDraft('A'))

  for (const title of ['Host filter', 'Service filter']) {
    const label = screen.getByText(title).closest('label')
    expect(label).not.toBeNull()
    expect(within(label!).getByText('(required)')).toBeInTheDocument()
  }
})

test('a filter section shows the errors it was given', () => {
  renderQueryForm(newRrdQueryDraft('A'), {
    host: [untranslated('Fill in at least one filter.')]
  })

  const alerts = screen.getAllByRole('alert')
  expect(alerts).toHaveLength(1)
  expect(alerts[0]).toHaveTextContent('Fill in at least one filter.')
})
