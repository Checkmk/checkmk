/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type {
  Dictionary,
  SingleChoiceEditable,
  ValidationMessage
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'
import FormSingleChoiceEditable from '@/form/private/forms/FormSingleChoiceEditable/FormSingleChoiceEditable.vue'

// The default client singleton captures `globalThis.fetch` at import time, before
// server.listen() patches it. Re-create it with a lazy fetch wrapper so MSW can intercept.
vi.mock('@/lib/rest-api-client/client', async (importOriginal) => {
  const mod = await importOriginal<Record<string, unknown>>()
  const createClientImpl = (await import('openapi-fetch')).default
  return {
    ...mod,
    default: createClientImpl({
      baseUrl: `${location.protocol}//${location.host}/api/internal`,
      credentials: 'include',
      headers: { Accept: 'application/json' },
      fetch: (...args: Parameters<typeof globalThis.fetch>) => globalThis.fetch(...args)
    })
  }
})

initializeComponentRegistry()

const mockSchema: Dictionary = {
  type: 'dictionary',
  title: 'Entity',
  help: '',
  validators: [],
  elements: [],
  groups: [],
  no_elements_text: '',
  additional_static_elements: []
}

const BASE = `${location.protocol}//${location.host}/api/internal`

const server = setupServer(
  http.get(`${BASE}/domain-types/notification_parameter/collections/:entity_type_specifier`, () =>
    HttpResponse.json({
      value: [
        { id: 'entity-1', title: 'Entity One' },
        { id: 'entity-2', title: 'Entity Two' }
      ]
    })
  ),
  http.get(`${BASE}/domain-types/form_spec/collections/:entity_type`, () =>
    HttpResponse.json({
      extensions: { schema: mockSchema, default_values: {} }
    })
  ),
  http.get(`${BASE}/objects/notification_parameter/:entity_id`, () =>
    HttpResponse.json({ extensions: {} })
  )
)

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterAll(() => server.close())
afterEach(() => {
  cleanup()
  server.resetHandlers()
})

function makeSpec(overrides: Partial<SingleChoiceEditable> = {}): SingleChoiceEditable {
  return {
    type: 'single_choice_editable',
    title: 'Select entity',
    help: '',
    validators: [],
    elements: [],
    config_entity_type: 'notification_parameter',
    config_entity_type_specifier: 'mail',
    allow_editing_existing_elements: true,
    ...overrides
  }
}

function renderComponent(
  props: {
    data?: string | null
    spec?: SingleChoiceEditable
    backendValidation?: Array<ValidationMessage>
  } = {}
) {
  const { data = null, spec = makeSpec(), backendValidation = [] } = props
  return render(FormSingleChoiceEditable, {
    props: {
      data,
      'onUpdate:data': () => {},
      spec,
      backendValidation
    }
  })
}

test('loads entities and shows no-elements text when none available', async () => {
  server.use(
    http.get(`${BASE}/domain-types/notification_parameter/collections/:entity_type_specifier`, () =>
      HttpResponse.json({ value: [] })
    )
  )
  renderComponent()
  await screen.findByLabelText('No options available')
})

test('uses inputHint as dropdown placeholder', async () => {
  renderComponent({ spec: makeSpec({ input_hint: 'Pick a parameter...' }) })
  await screen.findByLabelText('Pick a parameter...')
})

test('opens slide-in with readable new title when clicking create', async () => {
  renderComponent()
  await fireEvent.click(screen.getByRole('button', { name: /Create/ }))
  await screen.findByText('New mail parameter')
})

test('opens slide-in with readable edit title when clicking edit', async () => {
  renderComponent({ data: 'entity-1' })
  await fireEvent.click(await screen.findByRole('button', { name: /Edit/ }))
  await screen.findByText('Edit mail parameter')
})

test('does not show edit button for entity with hide_edit flag', async () => {
  server.use(
    http.get(`${BASE}/domain-types/notification_parameter/collections/:entity_type_specifier`, () =>
      HttpResponse.json({
        value: [{ id: 'entity-1', title: 'Entity One', extensions: { ui_hide_edit_button: true } }]
      })
    )
  )
  renderComponent({ data: 'entity-1' })
  await waitFor(() => {
    expect(screen.queryByRole('button', { name: /Edit/, hidden: true })).not.toBeInTheDocument()
  })
})

test('displays backend validation messages', async () => {
  renderComponent({
    backendValidation: [
      { location: [], message: 'This field is required', replacement_value: null }
    ]
  })
  await screen.findByText('This field is required')
})
