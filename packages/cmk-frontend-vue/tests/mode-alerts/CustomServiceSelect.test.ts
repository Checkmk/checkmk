/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { afterEach, expect, test } from 'vitest'
import { defineComponent, ref } from 'vue'

import CustomServiceSelect from '@/mode-alerts/CustomServiceSelect.vue'
import type { ServiceNameMatch } from '@/mode-alerts/types'

const FOUND: Array<[string, string]> = [
  ['web01', 'HTTP request duration'],
  ['web02', 'HTTP request duration'],
  ['db01', 'Query duration']
]

let sentPattern: string | null = null

useMswServer(
  restApiHttp.post(
    '/domain-types/telemetry_alert/actions/search_services/invoke',
    async ({ request, response }) => {
      const body = (await request.json()) as { service_match: { pattern: string } }
      sentPattern = body.service_match.pattern
      try {
        new RegExp(sentPattern)
      } catch (error) {
        return response.untyped(
          Response.json(
            {
              title: 'Bad Request',
              status: 400,
              fields: {
                'body.service_match.regex.pattern': {
                  loc: ['body', 'service_match', 'regex', 'pattern'],
                  msg: `Value error, Not a valid regular expression: ${(error as Error).message}`
                }
              }
            },
            { status: 400 }
          )
        )
      }
      const names = [
        ...new Set(
          FOUND.filter(([, name]) => new RegExp(`^(?:${sentPattern})`).test(name)).map(
            ([, name]) => name
          )
        )
      ].sort()
      return response(200).json({
        services: [],
        total: names.length,
        hidden: 0,
        units: [],
        undiscovered: 0,
        undiscovered_hosts: [],
        incomplete_configurations: [],
        unreachable_sites: [],
        service_names: names,
        service_names_truncated: false
      })
    }
  )
)

afterEach(() => {
  cleanup()
  sentPattern = null
})

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

test('each service name found is offered once, however many hosts have it', async () => {
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
    expect(sentPattern).toBe('.*duration\\.')
  })
})

test('a regular expression is searched anywhere in the name', async () => {
  renderSelect('regex')

  await open()
  await userEvent.type(await screen.findByRole('textbox', { name: 'filter' }), 'duration.')

  await waitFor(() => {
    expect(sentPattern).toBe('.*(?:duration.)')
  })
})

test('a pattern the server refuses shows its reason', async () => {
  renderSelect('regex')

  await open()
  await userEvent.type(await screen.findByRole('textbox', { name: 'filter' }), '(')

  expect(await screen.findByText(/^Not a valid regular expression: /)).toBeInTheDocument()
})
