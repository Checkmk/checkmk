/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
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

const ownedByContactGroupForm: FormSpec.CascadingSingleChoice = {
  type: 'cascading_single_choice',
  title: 'Editable by',
  label: null,
  help: '',
  validators: [],
  input_hint: '',
  no_elements_text: '',
  layout: 'vertical',
  elements: [
    {
      name: 'contact_group',
      title: 'Members of the contact group:',
      default_value: '',
      parameter_form: stringField('Contact group')
    }
  ]
}

const schemaWithCascadingOwner: Catalog = {
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
        {
          type: 'topic_element',
          name: 'owned_by',
          required: true,
          default_value: ['contact_group', ''],
          parameter_form: ownedByContactGroupForm
        },
        topicElement('share_with', 'Share with')
      ]
    }
  ]
}

const FORM_SPEC_URL = `${location.protocol}//${location.host}/api/internal/domain-types/form_spec/collections/:entity_type`
const LIST_PASSWORDS_URL = `${location.protocol}//${location.host}/api/internal/domain-types/passwordstore_password/collections/:entity_type_specifier`

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

function mockListPasswords(existingIds: string[] = []) {
  server.use(
    http.get(LIST_PASSWORDS_URL, () =>
      HttpResponse.json({
        value: existingIds.map((id) => ({ id, title: id }))
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
    mockListPasswords()
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

  test('shows validation error when ID is empty on save', async () => {
    mockFormSpec()
    render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await flushPromises()

    expect(screen.getAllByText('An empty value is not allowed here').length).toBeGreaterThan(0)
  })

  test('shows validation error when title is empty on save', async () => {
    mockFormSpec({
      general_props: { id: 'my-password', title: '', comment: '', docu_url: '' },
      password_props: { password: 'secret' }
    })
    mockListPasswords()
    render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await flushPromises()

    expect(screen.getAllByText('An empty value is not allowed here').length).toBeGreaterThan(0)
  })

  test('shows validation error when password is empty on save', async () => {
    mockFormSpec({
      general_props: { id: 'my-password', title: 'My Password', comment: '', docu_url: '' },
      password_props: { password: '' }
    })
    mockListPasswords()
    render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await flushPromises()

    expect(screen.getAllByText('An empty value is not allowed here').length).toBeGreaterThan(0)
  })

  test('treats whitespace-only ID as empty on save', async () => {
    mockFormSpec({
      general_props: { id: '   ', title: 'My Password', comment: '', docu_url: '' },
      password_props: { password: 'secret' }
    })
    render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await flushPromises()

    expect(screen.getAllByText('An empty value is not allowed here').length).toBeGreaterThan(0)
  })

  test('trims whitespace from ID and emits created on success', async () => {
    mockFormSpec({
      general_props: { id: '  my-pw  ', title: 'My Password', comment: '', docu_url: '' },
      password_props: { password: 'secret' }
    })
    mockListPasswords()
    const { emitted } = render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await flushPromises()

    expect(emitted().created).toMatchObject([[{ general_props: { id: 'my-pw' } }]])
  })

  test('shows validation error when password ID already exists', async () => {
    mockFormSpec({
      general_props: { id: 'existing-pw', title: 'My Password', comment: '', docu_url: '' },
      password_props: { password: 'secret' }
    })
    mockListPasswords(['existing-pw'])
    render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await flushPromises()

    expect(
      screen.getByText('This ID is already in use. Please choose another one.')
    ).toBeInTheDocument()
  })

  test('shows validation error when no contact group can own the password', async () => {
    server.use(
      http.get(FORM_SPEC_URL, () =>
        HttpResponse.json({
          extensions: {
            schema: schemaWithCascadingOwner,
            default_values: {
              general_props: { id: 'my-password', title: 'My Password', comment: '', docu_url: '' },
              password_props: {
                password: 'secret',
                owned_by: ['contact_group', ''],
                share_with: ''
              }
            }
          }
        })
      )
    )
    mockListPasswords()
    render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await flushPromises()

    expect(
      screen.getByText(
        'You need to be member of at least one contact group to be able to create a password.'
      )
    ).toBeInTheDocument()
  })

  test('emits created when a contact group owner is selected', async () => {
    server.use(
      http.get(FORM_SPEC_URL, () =>
        HttpResponse.json({
          extensions: {
            schema: schemaWithCascadingOwner,
            default_values: {
              general_props: { id: 'my-password', title: 'My Password', comment: '', docu_url: '' },
              password_props: {
                password: 'secret',
                owned_by: ['contact_group', 'linux'],
                share_with: ''
              }
            }
          }
        })
      )
    )
    mockListPasswords()
    const { emitted } = render(PasswordStoreSlideIn, { props: { open: true } })

    await flushPromises()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await flushPromises()

    expect(emitted().created).toMatchObject([
      [{ password_props: { owned_by: ['contact_group', 'linux'] } }]
    ])
  })
})
