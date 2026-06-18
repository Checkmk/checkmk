/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor, within } from '@testing-library/vue'
import type { GraphLineQueryAttributes } from 'cmk-shared-typing/typescript/graph_designer'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { defineComponent, ref } from 'vue'

import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'
import { KEY_IDENTS } from '@/metric-backend/attributeFilterAdapter'

// Keys the backend offers under each attribute-type key autocompleter, keyed by its ident.
const KEY_SUGGESTIONS: Record<string, string[]> = {
  [KEY_IDENTS.resource]: ['service.name'],
  [KEY_IDENTS.scope]: ['otel.library.name'],
  [KEY_IDENTS.datapoint]: ['http.method']
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

interface Models {
  resource: ReturnType<typeof ref<GraphLineQueryAttributes>>
  scope: ReturnType<typeof ref<GraphLineQueryAttributes>>
  datapoint: ReturnType<typeof ref<GraphLineQueryAttributes>>
}

function renderAttributes(initial: {
  resource?: GraphLineQueryAttributes
  scope?: GraphLineQueryAttributes
  datapoint?: GraphLineQueryAttributes
}): Models {
  const models: Models = {
    resource: ref(initial.resource ?? []),
    scope: ref(initial.scope ?? []),
    datapoint: ref(initial.datapoint ?? [])
  }
  const wrapper = defineComponent({
    components: { FormMetricBackendAttributes },
    setup() {
      return { models }
    },
    template: `
      <table><tbody>
        <FormMetricBackendAttributes
          v-model:resource-attributes="models.resource.value"
          v-model:scope-attributes="models.scope.value"
          v-model:data-point-attributes="models.datapoint.value"
        />
      </tbody></table>
    `
  })
  render(wrapper)
  return models
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

test('renders all preloaded attributes as pills', () => {
  renderAttributes({
    resource: [{ key: 'service.name', value: 'frontend' }],
    scope: [{ key: 'otel.library.name', value: 'http' }],
    datapoint: [{ key: 'http.method', value: 'GET' }]
  })

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
  renderAttributes({
    resource: [{ key: 'service.name', value: 'frontend' }],
    scope: [{ key: 'otel.library.name', value: 'http' }],
    datapoint: [{ key: 'http.method', value: 'GET' }]
  })

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

test('selecting a key writes it to the matching attribute list', async () => {
  const models = renderAttributes({})

  const filterInput = await openKeyFilter()
  await userEvent.type(filterInput, 'service')
  await userEvent.click(await screen.findByRole('option', { name: 'service.name' }))

  await waitFor(() => {
    expect(models.resource.value).toEqual([{ key: 'service.name', value: '' }])
  })
})
