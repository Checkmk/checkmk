/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test } from 'vitest'
import { defineComponent, ref } from 'vue'

import AssignHostStep from '@/mode-custom-services/steps/AssignHostStep.vue'

const API_BASE = `${location.protocol}//${location.host}/api/1.0`

// Hosts the injected otel_custom_service_host autocompleter offers ("name (ip)"
// label, host name as id — matching the backend autocompleter's Choices shape).
const HOSTS: Array<[string, string]> = [
  ['web01', 'web01 (10.0.0.1)'],
  ['db01', 'db01 (10.0.0.2)']
]

const server = setupServer(
  http.post(`${API_BASE}/objects/autocomplete/:ident`, async ({ request }) => {
    const { value: query } = (await request.json()) as { value: string }
    const matching = HOSTS.filter(([, label]) => !query || label.includes(query))
    return HttpResponse.json({ choices: matching.map(([id, value]) => ({ id, value })) })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
})
afterAll(() => server.close())

function renderStep(serviceName = '', hostName: string | null = null) {
  const service = ref(serviceName)
  const host = ref<string | null>(hostName)
  const wrapper = defineComponent({
    components: { AssignHostStep },
    setup() {
      return { service, host }
    },
    template: `<AssignHostStep v-model:service-name="service" v-model:host-name="host" />`
  })
  render(wrapper)
  return { service, host }
}

test('edits the service name', async () => {
  const { service } = renderStep('HTTP duration')
  const input = screen.getByDisplayValue('HTTP duration')
  await userEvent.clear(input)
  await userEvent.type(input, 'Latency')
  expect(service.value).toBe('Latency')
})

test('selects a host from the injected autocompleter suggestions', async () => {
  const { host } = renderStep('HTTP duration')
  const combobox = await screen.findByRole('combobox')
  await waitFor(() => expect(combobox).toBeEnabled(), { timeout: 10000 })
  void userEvent.click(combobox)
  await userEvent.click(
    await screen.findByRole('option', { name: 'web01 (10.0.0.1)' }, { timeout: 10000 })
  )
  expect(host.value).toBe('web01')
})

test('summarizes the service to be created once a host is chosen', () => {
  renderStep('HTTP duration', 'web01')
  expect(screen.getByText(/Services to be created/)).toHaveTextContent('(1)')
  expect(screen.getByText('web01')).toBeTruthy()
})
