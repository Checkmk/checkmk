/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import RowEditor from '@/graphing/designer/components/forms/RowEditor.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { type DesignerItem, newConstantDraft } from '@/graphing/designer/drafts'
import { isValid } from '@/graphing/designer/validation'

import { constantItem, filterDefinitions, metricBackendItem } from '../fixtures'

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
const THRESHOLDS = { warning: '#ffd000', critical: '#ff3232' }

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  mocks.fetchSuggestions.mockResolvedValue(new Response([]))
  mocks.fetchRestAPIDeprecated.mockResolvedValue({
    raiseForStatus: async () => {},
    json: async () => ({ choices: [] })
  })
})

afterEach(() => {
  vi.useRealTimers()
})

function renderEditor(seed: DesignerItem) {
  const store = useGraphItems(PALETTE)
  store.replaceAll([seed])
  const harness = defineComponent({
    setup() {
      useProvideFilterDefinitions({ definitions: filterDefinitions, groups: {} })
      return () => {
        const row = store.items.value.find((candidate) => candidate.id === seed.id)
        return row === undefined
          ? null
          : h(RowEditor, { row, store, thresholds: THRESHOLDS, issues: [] })
      }
    }
  })
  render(harness)
  return store
}

async function enterConstant(value: string): Promise<void> {
  await fireEvent.update(screen.getByRole('spinbutton', { name: /^Constant at/ }), value)
}

/** The pill takes a quantile; the store holds the percentile. */
async function enterQuantile(value: string): Promise<void> {
  await fireEvent.click(screen.getByRole('button', { name: /Edit consolidation/ }))
  await fireEvent.update(await screen.findByLabelText('Quantile (0 to 1)'), value)
}

function constantValue(store: ReturnType<typeof useGraphItems>): number | null {
  const row = store.items.value[0]
  if (row?.type !== 'constant') {
    throw new Error(`expected a constant source, got ${row?.type}`)
  }
  return row.value
}

function percentile(store: ReturnType<typeof useGraphItems>): number {
  const row = store.items.value[0]
  if (row?.type !== 'metric_backend' || row.consolidation_function.type !== 'histogram_quantile') {
    throw new Error(`expected a quantile-aggregated metric-backend source, got ${row?.type}`)
  }
  return row.consolidation_function.percentile
}

test('a source becoming valid says it was added to the graph', async () => {
  renderEditor(newConstantDraft('A', '#123456'))

  await enterConstant('42')

  expect(await screen.findByText('Preview added to graph')).toBeInTheDocument()
})

test('changing an already valid source says the preview was updated', async () => {
  renderEditor(constantItem('A'))

  await enterConstant('42')

  expect(await screen.findByText('Preview updated')).toBeInTheDocument()
})

test('an edit that leaves the source unfinished confirms nothing', async () => {
  const store = renderEditor(constantItem('A'))

  await enterConstant('')

  await waitFor(() => expect(constantValue(store)).toBeNull())
  expect(screen.queryByText(/^Preview/)).not.toBeInTheDocument()
})

test('a filled-in source the rules still reject confirms nothing', async () => {
  const store = renderEditor(metricBackendItem('A'))

  await enterQuantile('5')

  await waitFor(() => expect(percentile(store)).toBe(500))
  expect(isValid(store.items.value[0]!, filterDefinitions)).toBe(false)
  expect(screen.queryByText(/^Preview/)).not.toBeInTheDocument()
})

test('an edit that invalidates the source takes the confirmation back', async () => {
  const store = renderEditor(constantItem('A'))

  await enterConstant('42')
  expect(await screen.findByText('Preview updated')).toBeInTheDocument()

  await enterConstant('')

  await waitFor(() => expect(constantValue(store)).toBeNull())
  expect(screen.queryByText(/^Preview/)).not.toBeInTheDocument()
})

test('the row fields the table owns are not this form to confirm', async () => {
  const store = renderEditor(constantItem('A'))

  store.patch('A', { title: 'renamed', color: '#ff8400' })

  await waitFor(() => expect(store.items.value[0]).toMatchObject({ title: 'renamed' }))
  expect(screen.queryByText(/^Preview/)).not.toBeInTheDocument()
})

test('the confirmation dismisses itself and returns for the next edit', async () => {
  renderEditor(constantItem('A'))

  await enterConstant('42')
  expect(await screen.findByText('Preview updated')).toBeInTheDocument()

  vi.runAllTimers()
  await waitFor(() => expect(screen.queryByText('Preview updated')).not.toBeInTheDocument())

  await enterConstant('43')

  expect(await screen.findByText('Preview updated')).toBeInTheDocument()
})

test('the form is a group named after the source it edits', () => {
  renderEditor(constantItem('A'))

  expect(screen.getByRole('group', { name: 'Source A details' })).toBeInTheDocument()
})
