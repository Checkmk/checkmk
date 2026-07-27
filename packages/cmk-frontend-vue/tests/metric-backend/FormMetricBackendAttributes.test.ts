/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor, within } from '@testing-library/vue'
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { defineComponent, ref } from 'vue'

import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'
import { KEY_IDENTS } from '@/metric-backend/attributeFilterAdapter'

// Keys the backend offers under each attribute-kind key autocompleter, keyed by its ident.
const KEY_SUGGESTIONS: Record<string, string[]> = {
  [KEY_IDENTS.resource]: ['service.name'],
  [KEY_IDENTS.scope]: ['otel.library.name'],
  [KEY_IDENTS.data_point]: ['http.method']
}

const API_BASE = `${location.protocol}//${location.host}/api/1.0`

const server = setupServer(
  http.post(`${API_BASE}/objects/autocomplete/:ident`, async ({ params, request }) => {
    const ident = params.ident as string
    const { value: query } = (await request.json()) as { value: string }
    const keys = KEY_SUGGESTIONS[ident] ?? []
    const matching = query ? keys.filter((key) => key.includes(query)) : keys
    return HttpResponse.json({ choices: matching.map((key) => ({ id: key, value: key })) })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
})
afterAll(() => server.close())

type AttributeFilterModel = ReturnType<typeof ref<AttributeFilter | null | undefined>>

function renderAttributes(attributeFilter?: AttributeFilter | null): AttributeFilterModel {
  const model = ref<AttributeFilter | null | undefined>(attributeFilter)
  const wrapper = defineComponent({
    components: { FormMetricBackendAttributes },
    setup() {
      return { model }
    },
    template: `
      <table><tbody>
        <FormMetricBackendAttributes v-model:attribute-filter="model" />
      </tbody></table>
    `
  })
  render(wrapper)
  return model
}

const THREE_ATTRIBUTES: AttributeFilter = {
  type: 'and',
  conjuncts: [
    { type: 'equals', key: { kind: 'resource', name: 'service.name' }, value: 'frontend' },
    { type: 'equals', key: { kind: 'scope', name: 'otel.library.name' }, value: 'http' },
    { type: 'equals', key: { kind: 'data_point', name: 'http.method' }, value: 'GET' }
  ]
}

function pillLabels(): string[] {
  return screen
    .getAllByRole('button', { name: /^Edit condition:/ })
    .map((button) => button.getAttribute('aria-label') ?? '')
}

function pillFor(key: string): HTMLElement {
  const group = screen.getByRole('group', { name: 'Attributes' })
  const pill = within(group)
    .getAllByRole('group')
    .find((candidate) =>
      within(candidate)
        .queryByRole('button', { name: /^Edit condition:/ })
        ?.getAttribute('aria-label')
        ?.includes(key)
    )
  if (!pill) {
    throw new Error(`No pill found for key ${key}`)
  }
  return pill
}

async function openKeyFilter(): Promise<HTMLElement> {
  await userEvent.click(screen.getByRole('button', { name: 'Add condition' }))
  const keyCombobox = await screen.findByRole('combobox', { name: 'Attribute key' })
  await waitFor(() => {
    expect(keyCombobox.getAttribute('aria-expanded')).toBe('true')
  })
  return screen.getByRole('textbox', { name: 'filter' })
}

test('renders the filter conditions as pills', () => {
  renderAttributes(THREE_ATTRIBUTES)

  const labels = pillLabels()
  expect(labels).toHaveLength(3)
  expect(labels).toEqual(
    expect.arrayContaining([
      expect.stringContaining('service.name'),
      expect.stringContaining('otel.library.name'),
      expect.stringContaining('http.method')
    ])
  )
})

test('removing a pill removes it and leaves the other pills untouched', async () => {
  renderAttributes(THREE_ATTRIBUTES)

  await userEvent.click(
    within(pillFor('otel.library.name')).getByRole('button', { name: 'Remove condition' })
  )

  await waitFor(() => {
    expect(pillLabels()).toHaveLength(2)
  })
  const labels = pillLabels()
  expect(labels).toEqual(
    expect.arrayContaining([
      expect.stringContaining('service.name'),
      expect.stringContaining('http.method')
    ])
  )
  expect(labels.some((label) => label.includes('otel.library.name'))).toBe(false)
})

test('a key with no value keeps the emitted filter empty', async () => {
  const model = renderAttributes()

  const filterInput = await openKeyFilter()
  await userEvent.type(filterInput, 'service')
  // Wait for the debounce to settle: un-keyed <li>s mean clicking mid-re-render hits the wrong option.
  await screen.findByRole('option', { name: 'service' })
  await userEvent.click(screen.getByRole('option', { name: 'service.name' }))

  // The key is set, but with no value the condition is invalid, so the filter stays empty.
  await waitFor(() => {
    expect(model.value).toEqual({ type: 'and', conjuncts: [] })
  })
})

test('emits an empty AND (match everything) when there are no attributes', () => {
  expect(renderAttributes().value).toEqual({ type: 'and', conjuncts: [] })
})

test('initializes the pills from a provided attribute filter, including exists', () => {
  renderAttributes({
    type: 'and',
    conjuncts: [
      { type: 'equals', key: { kind: 'resource', name: 'service.name' }, value: 'frontend' },
      { type: 'exists', key: { kind: 'scope', name: 'otel.library.name' } }
    ]
  })

  const labels = pillLabels()
  expect(labels).toHaveLength(2)
  expect(labels).toEqual(
    expect.arrayContaining([
      expect.stringContaining('service.name'),
      expect.stringContaining('otel.library.name')
    ])
  )
})
