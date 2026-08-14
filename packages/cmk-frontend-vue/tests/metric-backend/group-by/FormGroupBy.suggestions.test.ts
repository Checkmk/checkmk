/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { defineComponent, ref } from 'vue'

import { KEY_IDENTS, buildAutocompleteContext } from '@/metric-backend/attributeFilterAdapter'
import { useAttributeKeySuggestions } from '@/metric-backend/attributeKeySuggestions'
import FormGroupBy from '@/metric-backend/group-by/FormGroupBy.vue'
import type { GroupByModel } from '@/metric-backend/group-by/types'

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

function renderWidget(initial: Partial<GroupByModel> = {}) {
  const model = ref<GroupByModel>({ function: 'avg', params: {}, keys: [], ...initial })
  const wrapper = defineComponent({
    components: { FormGroupBy },
    setup() {
      const { querySuggestions, resolveAttributeKind, suggestionRevision } =
        useAttributeKeySuggestions(() => buildAutocompleteContext([], { metricName: 'demo' }))
      return { model, querySuggestions, resolveAttributeKind, suggestionRevision }
    },
    template: `
      <FormGroupBy
        v-model="model"
        input-type="float"
        :query-suggestions="querySuggestions"
        :suggestion-revision="suggestionRevision"
        :resolve-attribute-kind="resolveAttributeKind"
      />
    `
  })
  render(wrapper)
  return { model }
}

test('re-editing a group key repopulates the key dropdown from the backend (CMK-37460)', async () => {
  renderWidget({ keys: [{ id: '1', attributeKind: 'resource', attributeKey: 'service.name' }] })

  await userEvent.click(screen.getByRole('button', { name: /Edit group by/ }))
  const keyCombobox = await screen.findByRole('combobox', { name: 'Attribute key' })
  if (keyCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(keyCombobox)
  }
  await waitFor(() => {
    expect(keyCombobox.getAttribute('aria-expanded')).toBe('true')
  })
  await userEvent.clear(screen.getByRole('textbox', { name: 'filter' }))

  expect(await screen.findByRole('option', { name: 'otel.library.name' })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'http.method' })).toBeInTheDocument()
})
