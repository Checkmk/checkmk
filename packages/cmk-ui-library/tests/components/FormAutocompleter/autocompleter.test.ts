/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ErrorResponse, Response, WarningResponse } from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'

// The component library talks to the autocompleter over the REST API. Mocking
// the transport here rather than the module keeps the request itself under
// test: the route it goes to, the body it sends and the shape it reads back.
const ROUTE = '*/api/internal/objects/autocomplete/:autocomplete_id'

let lastRequest: { id: string; body: unknown } | null = null

const server = useMswServer(
  http.post(ROUTE, async ({ request, params }) => {
    lastRequest = { id: params['autocomplete_id'] as string, body: await request.json() }
    return HttpResponse.json({ choices: [{ id: 'linux01', value: 'Linux 01' }] })
  })
)

afterEach(() => {
  lastRequest = null
})

function autocompleter(): Autocompleter {
  return {
    fetch_method: 'rest_autocomplete',
    data: { ident: 'config_hostname', params: { world: 'config' } }
  } as Autocompleter
}

test('sends the query and the params to the autocompleter named in the data', async () => {
  const result = await fetchSuggestions(autocompleter(), 'lin')

  expect(result).toBeInstanceOf(Response)
  expect(lastRequest).toEqual({
    id: 'config_hostname',
    body: { value: 'lin', parameters: { world: 'config' } }
  })
})

test('leaves out the params a producer never set', async () => {
  // The generated params carry a null for every field the producer left unset.
  // Sending those makes the autocompleters read a null where they expect their
  // own default, which crashes the ones that reach into `context`.
  const sparse = {
    fetch_method: 'rest_autocomplete',
    data: { ident: 'label', params: { world: 'core', context: null, object_type: null } }
  } as unknown as Autocompleter

  await fetchSuggestions(sparse, 'lin')

  expect(lastRequest?.body).toEqual({ value: 'lin', parameters: { world: 'core' } })
})

test('keeps a choice that carries no id, so its hint still shows', async () => {
  // A null id marks a suggestion the user cannot select, which is how the
  // backend reports that it truncated the list.
  server.use(
    http.post(ROUTE, () =>
      HttpResponse.json({
        choices: [
          { id: null, value: '(Max suggestions reached, be more specific)' },
          { id: 'linux01', value: 'Linux 01' }
        ]
      })
    )
  )

  const result = (await fetchSuggestions(autocompleter(), 'lin')) as Response

  expect(result.choices).toEqual([
    { name: null, title: '(Max suggestions reached, be more specific)' },
    { name: 'linux01', title: 'Linux 01' }
  ])
})

test('turns the returned choices into suggestions', async () => {
  const result = (await fetchSuggestions(autocompleter(), 'lin')) as Response

  expect(result.choices).toEqual([{ name: 'linux01', title: 'Linux 01' }])
})

test('a warning in the response keeps the choices and carries the message', async () => {
  server.use(
    http.post(ROUTE, () =>
      HttpResponse.json({
        choices: [{ id: 'linux01', value: 'Linux 01' }],
        warning: 'The backend is unavailable.'
      })
    )
  )

  const result = (await fetchSuggestions(autocompleter(), 'lin')) as WarningResponse

  expect(result).toBeInstanceOf(WarningResponse)
  expect(result.warning).toBe('The backend is unavailable.')
  expect(result.choices).toEqual([{ name: 'linux01', title: 'Linux 01' }])
})

test('an error response is reported rather than thrown', async () => {
  server.use(
    http.post(ROUTE, () =>
      HttpResponse.json({ title: 'Invalid input', detail: 'no such world' }, { status: 400 })
    )
  )

  const result = await fetchSuggestions(autocompleter(), 'lin')

  expect(result).toBeInstanceOf(ErrorResponse)
  expect((result as ErrorResponse).error).toContain('Invalid input')
})

test('the ajax fetch method still reaches the REST API', async () => {
  // The plugin API and the legacy frontend still know `ajax_vs_autocomplete`,
  // so a producer may keep sending it. It must not fail here.
  const legacy = { ...autocompleter(), fetch_method: 'ajax_vs_autocomplete' } as Autocompleter

  const result = await fetchSuggestions(legacy, 'lin')

  expect(result).toBeInstanceOf(Response)
  expect(lastRequest?.id).toBe('config_hostname')
})
