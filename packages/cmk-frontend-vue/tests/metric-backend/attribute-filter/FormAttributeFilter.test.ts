/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import { Response } from '@/components/CmkSuggestions/suggestions'

import FormAttributeFilter from '@/metric-backend/attribute-filter/FormAttributeFilter.vue'
import { pillLabel } from '@/metric-backend/attribute-filter/pill-label'
import type { AttributeFilterModel, AttributeType } from '@/metric-backend/attribute-filter/types'

const KEY_SUGGESTIONS = [
  { name: 'http.method', title: 'http.method' },
  { name: 'service.name', title: 'service.name' },
  { name: 'foo.bar', title: 'foo.bar' }
]

function makeModel(): AttributeFilterModel {
  return [
    {
      id: 'pill-a',
      attributeType: null,
      key: '',
      operator: 'eq',
      value: '',
      connector: 'AND'
    },
    {
      id: 'pill-b',
      attributeType: 'scope',
      key: 'otel.library.name',
      operator: 'eq',
      value: '',
      connector: 'AND'
    }
  ]
}

function querySuggestions(query: string): Promise<Response> {
  const lower = query.toLowerCase()
  return Promise.resolve(
    new Response(KEY_SUGGESTIONS.filter((s) => s.name.toLowerCase().includes(lower)))
  )
}

function renderForm(
  initial: AttributeFilterModel,
  resolve?: (key: string) => AttributeType
): { model: ReturnType<typeof ref<AttributeFilterModel>> } {
  const model = ref<AttributeFilterModel>(initial)
  const wrapperComponent = defineComponent({
    components: { FormAttributeFilter },
    setup() {
      return { model, querySuggestions, resolveAttributeType: resolve }
    },
    template: `
      <FormAttributeFilter
        v-model="model"
        :query-suggestions="querySuggestions"
        :resolve-attribute-type="resolveAttributeType"
      />
    `
  })
  render(wrapperComponent)
  return { model }
}

function pillsInOrder(): HTMLElement[] {
  const outerGroup = screen.getByRole('group', { name: 'Attribute filter' })
  return within(outerGroup).getAllByRole('group')
}

async function pickKey(pill: HTMLElement, name: string): Promise<void> {
  const keyCombobox = within(pill).getByRole('combobox', { name: 'Attribute key' })
  await userEvent.click(keyCombobox)
  const filter = screen.getByRole('textbox', { name: 'filter' })
  // In callback-filtered mode the filter is pre-populated with the current
  // selection's title; clear it so the typed query starts from scratch.
  await userEvent.clear(filter)
  await userEvent.type(filter, name)
  await userEvent.click(await screen.findByRole('option', { name }))
}

test('picking a known key applies key and inferred attributeType in one mutation', async () => {
  const { model } = renderForm(makeModel(), (key) => (key === 'http.method' ? 'datapoint' : null))
  // The pill emits only `update:key`; the parent owns the resolver and merges
  // the inferred attributeType into the same model mutation. A regression that
  // re-splits this into two sequential emits would let the second write
  // overwrite the first via `defineModel`'s deferred prop propagation.
  await pickKey(pillsInOrder()[0]!, 'http.method')

  expect(model.value![0]).toMatchObject({
    id: 'pill-a',
    key: 'http.method',
    attributeType: 'datapoint'
  })
  // Pill B must be untouched — guards against any cross-row contamination
  // that a sloppier identity strategy could introduce.
  expect(model.value![1]).toMatchObject({
    id: 'pill-b',
    key: 'otel.library.name',
    attributeType: 'scope'
  })
})

test('picking a key without a resolver hit preserves the existing attributeType', async () => {
  // Seed pill-a with a non-null attributeType so the assertion exercises the
  // "no inference → leave the type alone" path. A free-text key edit on a
  // resolver-less form must not silently wipe a user-picked type.
  const initial = makeModel()
  initial[0]!.attributeType = 'resource'
  initial[0]!.key = 'service.name'
  const { model } = renderForm(initial)
  await pickKey(pillsInOrder()[0]!, 'foo.bar')

  expect(model.value![0]).toMatchObject({ key: 'foo.bar', attributeType: 'resource' })
})

test('manual attributeType change persists on the targeted row', async () => {
  const { model } = renderForm(makeModel())
  const typeCombobox = within(pillsInOrder()[1]!).getByRole('combobox', { name: 'Attribute type' })
  await userEvent.click(typeCombobox)
  await userEvent.click(await screen.findByRole('option', { name: 'Data point' }))

  expect(model.value![1]!.attributeType).toBe('datapoint')
  expect(model.value![0]!.attributeType).toBe(null)
})

test('picking a key with no resolver hit auto-opens the type dropdown', async () => {
  renderForm(makeModel(), () => null)
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'foo.bar')

  const typeCombobox = within(pillA).getByRole('combobox', { name: 'Attribute type' })
  await waitFor(() => {
    expect(typeCombobox.getAttribute('aria-expanded')).toBe('true')
  })
})

test('picking a key with a resolver hit does not auto-open the type dropdown', async () => {
  renderForm(makeModel(), (key) => (key === 'http.method' ? 'datapoint' : null))
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'http.method')

  const typeCombobox = within(pillA).getByRole('combobox', { name: 'Attribute type' })
  // Give the watcher's nextTick a chance to run; aria-expanded must stay 'false'.
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(typeCombobox.getAttribute('aria-expanded')).toBe('false')
})

test('remove drops the targeted row by id, leaving siblings intact', async () => {
  const { model } = renderForm(makeModel())
  const pillA = pillsInOrder()[0]!
  const pillALabel = pillLabel(makeModel()[0]!)
  await userEvent.click(within(pillA).getByRole('button', { name: 'Remove condition' }))

  expect(model.value).toHaveLength(1)
  expect(model.value![0]!.id).toBe('pill-b')
  // The removed pill must be gone from the DOM, not just from the model.
  expect(screen.queryByRole('group', { name: pillALabel })).toBeNull()
})
