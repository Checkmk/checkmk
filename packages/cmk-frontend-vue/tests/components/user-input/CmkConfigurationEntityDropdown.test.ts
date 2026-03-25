/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import type { Dictionary } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import CmkConfigurationEntityDropdown from '@/components/user-input/CmkConfigurationEntityDropdown/CmkConfigurationEntityDropdown.vue'

import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

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

const entityType = 'notification_parameter' as ConfigEntityType
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

function renderComponent(
  props: {
    modelValue?: string | null
    allowEditingExistingElements?: boolean
    validation?: Array<string>
    label?: string
    inputHint?: string
  } = {}
) {
  const { modelValue = null, ...rest } = props
  return render(CmkConfigurationEntityDropdown, {
    props: {
      modelValue,
      'onUpdate:modelValue': () => {},
      configEntityType: entityType,
      configEntityTypeSpecifier: 'mail',
      label: 'Select entity',
      ...rest
    }
  })
}

test('shows no-elements text when no entities available', async () => {
  server.use(
    http.get(`${BASE}/domain-types/notification_parameter/collections/:entity_type_specifier`, () =>
      HttpResponse.json({ value: [] })
    )
  )
  renderComponent()
  await screen.findByLabelText('No options available')
})

test('uses inputHint as dropdown placeholder', async () => {
  renderComponent({ inputHint: 'Pick a parameter...' })
  await screen.findByLabelText('Pick a parameter...')
})

test('always shows create button', async () => {
  renderComponent()
  await screen.findByRole('button', { name: /Create/ })
})

test('does not show edit button when nothing is selected', () => {
  renderComponent({ modelValue: null, allowEditingExistingElements: true })
  expect(screen.queryByRole('button', { name: /Edit/ })).not.toBeInTheDocument()
})

test('shows edit button when an item is selected', async () => {
  renderComponent({ modelValue: 'entity-1', allowEditingExistingElements: true })
  expect(await screen.findByRole('button', { name: /Edit/ })).toBeVisible()
})

test('does not show edit button when allowEditingExistingElements is false', async () => {
  renderComponent({ modelValue: 'entity-1', allowEditingExistingElements: false })
  expect(screen.queryByRole('button', { name: /Edit/, hidden: true })).not.toBeInTheDocument()
})

test('does not show edit button for entity with hide_edit flag', async () => {
  server.use(
    http.get(`${BASE}/domain-types/notification_parameter/collections/:entity_type_specifier`, () =>
      HttpResponse.json({
        value: [{ id: 'entity-1', title: 'Entity One', extensions: { ui_hide_edit_button: true } }]
      })
    )
  )
  renderComponent({ modelValue: 'entity-1', allowEditingExistingElements: true })
  await waitFor(() => {
    expect(screen.queryByRole('button', { name: /Edit/, hidden: true })).not.toBeInTheDocument()
  })
})

test('opens slide-in with new title when clicking create', async () => {
  renderComponent()
  await fireEvent.click(screen.getByRole('button', { name: /Create/ }))
  await screen.findByText('New mail parameter')
})

test('opens slide-in with edit title when clicking edit', async () => {
  renderComponent({ modelValue: 'entity-1', allowEditingExistingElements: true })
  await fireEvent.click(await screen.findByRole('button', { name: /Edit/ }))
  await screen.findByText('Edit mail parameter')
})

test('closes slide-in when close button is clicked', async () => {
  renderComponent()
  await fireEvent.click(screen.getByRole('button', { name: /Create/ }))
  await screen.findByText('New mail parameter')
  await fireEvent.click(screen.getByRole('button', { name: 'Close' }))
  await waitFor(() => {
    expect(screen.queryByText('New mail parameter')).not.toBeInTheDocument()
  })
})

test('displays validation messages', async () => {
  renderComponent({ validation: ['This field is required'] })
  await screen.findByText('This field is required')
})

test('does not display validation messages when no validation prop', async () => {
  renderComponent()
  expect(screen.queryByText('This field is required')).not.toBeInTheDocument()
})
