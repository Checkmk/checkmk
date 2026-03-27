/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import type { Catalog } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

import PasswordStoreSlideIn from '@/mode-otel/otel-configuration-steps/PasswordStoreSlideIn.vue'

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

function stringField(title: string) {
  return {
    type: 'string' as const,
    title,
    label: null,
    help: '',
    validators: [],
    input_hint: null,
    autocompleter: null,
    field_size: 'MEDIUM' as const
  }
}

function topicElement(name: string, title: string) {
  return {
    type: 'topic_element' as const,
    name,
    required: true,
    default_value: '',
    parameter_form: stringField(title)
  }
}

// Mirrors the structure returned by get_password_slidein_schema on the backend.
// Uses string fields for all entries to keep the test schema simple.
const passwordCatalogSchema: Catalog = {
  type: 'catalog',
  title: 'New password',
  help: '',
  validators: [],
  elements: [
    {
      name: 'general_props',
      title: 'General properties',
      locked: null,
      elements: [
        topicElement('id', 'Unique ID'),
        topicElement('title', 'Title'),
        topicElement('comment', 'Comment'),
        topicElement('docu_url', 'Documentation URL')
      ]
    },
    {
      name: 'password_props',
      title: 'Password properties',
      locked: null,
      elements: [
        topicElement('password', 'Password'),
        topicElement('owned_by', 'Editable by'),
        topicElement('share_with', 'Share with')
      ]
    }
  ]
}

const defaultValues = {
  general_props: { id: '', title: '', comment: '', docu_url: '' },
  password_props: { password: '', owned_by: '', share_with: '' }
}

const FORM_SPEC_URL = `${location.protocol}//${location.host}/api/internal/domain-types/form_spec/collections/:entity_type`

const server = setupServer()

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterAll(() => server.close())

function mockFormSpec(overrideDefaultValues: Record<string, unknown> = defaultValues) {
  server.use(
    http.get(FORM_SPEC_URL, () =>
      HttpResponse.json({
        extensions: {
          schema: passwordCatalogSchema,
          default_values: overrideDefaultValues
        }
      })
    )
  )
}

describe('PasswordStoreSlideIn', () => {
  afterEach(() => {
    cleanup()
    server.resetHandlers()
  })

  test('fetches the form spec from the passwordstore_password endpoint', async () => {
    let capturedRequest: Request | undefined
    server.use(
      http.get(FORM_SPEC_URL, ({ request }) => {
        capturedRequest = request
        return HttpResponse.json({
          extensions: { schema: passwordCatalogSchema, default_values: defaultValues }
        })
      })
    )
    render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()

    const url = new URL(capturedRequest!.url)
    expect(url.pathname).toContain('passwordstore_password')
    expect(url.searchParams.get('entity_type_specifier')).toBe('passwordstore_password')
  })

  test('shows password store fields when open', async () => {
    mockFormSpec()
    render(PasswordStoreSlideIn, { props: { open: true } })

    await screen.findByText('General properties')
    expect(screen.getByText('Unique ID')).toBeInTheDocument()
    expect(screen.getByText('Title')).toBeInTheDocument()
    expect(screen.getByText('Comment')).toBeInTheDocument()
    expect(screen.getByText('Documentation URL')).toBeInTheDocument()

    await screen.findByText('Password properties')
    expect(screen.getByText('Password')).toBeInTheDocument()
    expect(screen.getByText('Editable by')).toBeInTheDocument()
    expect(screen.getByText('Share with')).toBeInTheDocument()
  })

  test('emits close when the close button is clicked', async () => {
    mockFormSpec()
    const { emitted } = render(PasswordStoreSlideIn, { props: { open: true } })

    const closeButton = await screen.findByRole('button', { name: 'Close' })
    await fireEvent.click(closeButton)

    expect(emitted().close).toBeTruthy()
  })

  test('emits close when Cancel is clicked', async () => {
    mockFormSpec()
    const { emitted } = render(PasswordStoreSlideIn, { props: { open: true } })

    const cancelButton = await screen.findByRole('button', { name: 'Cancel' })
    await fireEvent.click(cancelButton)

    expect(emitted().close).toBeTruthy()
  })

  test('emits created with password configuration after clicking Save', async () => {
    mockFormSpec({
      general_props: { id: 'my-password', title: 'My Password', comment: '', docu_url: '' },
      password_props: { password: 'secret' }
    })
    const { emitted } = render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()

    const saveButton = screen.getByRole('button', { name: 'Save' })
    await fireEvent.click(saveButton)
    await flushPromises()

    expect(emitted().created).toMatchObject([
      [
        {
          general_props: { id: 'my-password', title: 'My Password' },
          password_props: { password: 'secret' }
        }
      ]
    ])
  })
})
