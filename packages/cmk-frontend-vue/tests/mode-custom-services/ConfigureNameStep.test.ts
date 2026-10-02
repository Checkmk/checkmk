/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, test } from 'vitest'
import { defineComponent, ref } from 'vue'

import ConfigureNameStep from '@/mode-custom-services/steps/ConfigureNameStep.vue'

const API_BASE = `${location.protocol}//${location.host}/api/internal`
const LIST_URL = `${API_BASE}/domain-types/custom_service/collections/all`

const server = setupServer()

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
})
afterAll(() => server.close())

function serveExisting(ids: string[]) {
  server.use(
    http.get(LIST_URL, () =>
      HttpResponse.json({ value: ids.map((id) => ({ id, domainType: 'custom_service' })) })
    )
  )
}

function serveListError() {
  server.use(http.get(LIST_URL, () => HttpResponse.json({ title: 'Boom' }, { status: 500 })))
}

function renderStep(initialName = '', readOnly = false) {
  const name = ref(initialName)
  const stepRef = ref<InstanceType<typeof ConfigureNameStep>>()
  render(
    defineComponent({
      components: { ConfigureNameStep },
      setup: () => ({ name, stepRef, readOnly }),
      template: `<ConfigureNameStep ref="stepRef" v-model:configuration-name="name" :read-only="readOnly" />`
    })
  )
  return { name, stepRef }
}

async function renderLoadedStep(initialName = '') {
  const rendered = renderStep(initialName)
  await waitFor(() => expect(rendered.name.value).not.toBe(''))
  return rendered
}

describe('prefill', () => {
  test('suggests the first slot when no custom service exists', async () => {
    serveExisting([])
    const { name } = renderStep()
    await waitFor(() => expect(name.value).toBe('custom_service_config_1'))
  })

  test('suggests the slot after the highest existing one', async () => {
    serveExisting(['custom_service_config_1', 'custom_service_config_4', 'other'])
    const { name } = renderStep()
    await waitFor(() => expect(name.value).toBe('custom_service_config_5'))
  })

  test('suggests the first slot when the list cannot be loaded', async () => {
    serveListError()
    const { name } = renderStep()
    await waitFor(() => expect(name.value).toBe('custom_service_config_1'))
  })

  test('accepts and keeps what the user typed while the suggestion is loading', async () => {
    let releaseList: () => void = () => {}
    const listReleased = new Promise<void>((resolve) => {
      releaseList = resolve
    })
    let suggestionAnswered = false
    serveExisting([])
    server.use(
      http.get(
        LIST_URL,
        async () => {
          await listReleased
          suggestionAnswered = true
          return HttpResponse.json({ value: [] })
        },
        { once: true }
      )
    )
    const { name, stepRef } = renderStep()
    await userEvent.type(screen.getByRole('textbox'), 'typed_name')
    expect(await stepRef.value!.validate()).toBe(true)
    releaseList()
    await waitFor(() => expect(suggestionAnswered).toBe(true))
    await new Promise((r) => setTimeout(r, 0))
    expect(name.value).toBe('typed_name')
  })

  test('keeps a name that is already set', async () => {
    let listRequests = 0
    server.use(
      http.get(LIST_URL, () => {
        listRequests += 1
        return HttpResponse.json({ value: [] })
      })
    )
    const { name, stepRef } = renderStep('my_name')
    await waitFor(() => expect(stepRef.value).toBeDefined())
    expect(await stepRef.value!.validate()).toBe(true)
    expect(listRequests).toBe(1)
    expect(name.value).toBe('my_name')
  })
})

describe('validate', () => {
  test('accepts a free, well-formed name', async () => {
    serveExisting([])
    const { stepRef } = await renderLoadedStep()
    expect(await stepRef.value!.validate()).toBe(true)
  })

  test('rejects a malformed name and shows the error at the field', async () => {
    serveExisting([])
    const { name, stepRef } = await renderLoadedStep()
    const input = screen.getByDisplayValue(name.value)
    await userEvent.clear(input)
    await userEvent.type(input, '1 bad')
    expect(await stepRef.value!.validate()).toBe(false)
    await screen.findByText(
      'The name must only consist of letters, digits, dash and underscore and it must start with a letter or underscore.'
    )
  })

  test('rejects a name created after the step was opened', async () => {
    serveExisting([])
    const { name, stepRef } = await renderLoadedStep()
    serveExisting([name.value])
    expect(await stepRef.value!.validate()).toBe(false)
    await screen.findByText(
      'A configuration with this name already exists. Choose a different name.'
    )
  })

  test('blocks when the names in use cannot be checked', async () => {
    serveExisting([])
    const { stepRef } = await renderLoadedStep()
    serveListError()
    expect(await stepRef.value!.validate()).toBe(false)
    await screen.findByText('Failed to validate the configuration name. Please try again.')
  })
})

describe('read-only', () => {
  test('shows the stored name as text and accepts it without asking the server', async () => {
    let listRequests = 0
    server.use(
      http.get(LIST_URL, () => {
        listRequests += 1
        return HttpResponse.json({ value: [{ id: 'stored_name', domainType: 'custom_service' }] })
      })
    )
    const { stepRef } = renderStep('stored_name', true)
    await waitFor(() => expect(stepRef.value).toBeDefined())

    expect(screen.getByText('stored_name')).toBeTruthy()
    expect(screen.queryByRole('textbox')).toBeNull()
    expect(await stepRef.value!.validate()).toBe(true)
    expect(listRequests).toBe(0)
  })
})
