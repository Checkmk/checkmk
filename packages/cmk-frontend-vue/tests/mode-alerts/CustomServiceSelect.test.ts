/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import CustomServiceSelect from '@/mode-alerts/CustomServiceSelect.vue'
import type { ServiceNameMatch } from '@/mode-alerts/types'

// The default client singleton captures `globalThis.fetch` at import time, before
// server.listen() patches it. Re-create it with a lazy fetch wrapper so MSW can intercept.
vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
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

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/service/collections/all`

const DISCOVERED: Array<[string, string]> = [
  ['web01', 'HTTP request duration'],
  ['web02', 'HTTP request duration'],
  ['db01', 'Query duration']
]

let sentPattern: string | null = null

const server = setupServer(
  http.post(ENDPOINT, async ({ request }) => {
    const body = (await request.json()) as {
      query: { expr: Array<{ left: string; right: string }> }
    }
    sentPattern = body.query.expr.find((condition) => condition.left === 'description')?.right ?? ''
    const matching = DISCOVERED.filter(([, name]) => new RegExp(sentPattern!).test(name))
    return HttpResponse.json({
      id: 'all',
      links: [],
      value: matching.map(([hostName, serviceName]) => ({
        extensions: { host_name: hostName, description: serviceName }
      }))
    })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  cleanup()
  sentPattern = null
  server.resetHandlers()
})
afterAll(() => server.close())

function renderSelect(matchType: ServiceNameMatch = 'exact') {
  const serviceName = ref<string | null>(null)
  const wrapper = defineComponent({
    components: { CustomServiceSelect },
    setup() {
      return { serviceName, matchType }
    },
    template: `<CustomServiceSelect v-model="serviceName" :match-type="matchType" />`
  })
  render(wrapper)
  return { serviceName }
}

async function open(): Promise<void> {
  const trigger = screen.getByRole('combobox', { name: 'Service name' })
  await waitFor(() => expect(trigger).toBeEnabled())
  void userEvent.click(trigger)
}

test('each discovered service name is offered once, however many hosts have it', async () => {
  renderSelect()

  await open()

  expect(await screen.findByRole('option', { name: 'HTTP request duration' })).toBeInTheDocument()
  expect(screen.getAllByRole('option', { name: 'HTTP request duration' })).toHaveLength(1)
})

test('choosing an offered name selects it', async () => {
  const { serviceName } = renderSelect()

  await open()
  await userEvent.click(await screen.findByRole('option', { name: 'Query duration' }))

  expect(serviceName.value).toBe('Query duration')
})

test('a name no service has can still be selected as typed', async () => {
  const { serviceName } = renderSelect('regex')

  await open()
  await userEvent.type(await screen.findByRole('textbox', { name: 'filter' }), 'duration$')
  await userEvent.click(await screen.findByRole('option', { name: 'duration$' }))

  expect(serviceName.value).toBe('duration$')
})

test('an exact match looks for the query literally', async () => {
  renderSelect('exact')

  await open()
  await userEvent.type(await screen.findByRole('textbox', { name: 'filter' }), 'duration.')

  await waitFor(() => {
    expect(sentPattern).toBe('duration\\.')
  })
})

test('a regular expression is passed through untouched', async () => {
  renderSelect('regex')

  await open()
  await userEvent.type(await screen.findByRole('textbox', { name: 'filter' }), 'duration.')

  await waitFor(() => {
    expect(sentPattern).toBe('duration.')
  })
})
