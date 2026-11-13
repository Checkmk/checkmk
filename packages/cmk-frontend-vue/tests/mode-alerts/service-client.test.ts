/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { afterEach, expect, test } from 'vitest'

import {
  type ServiceSearchResult,
  patternErrorOf,
  searchServices,
  suggestionPattern
} from '@/mode-alerts/service-client'

const SEARCH = '/domain-types/telemetry_alert/actions/search_services/invoke'

const NOTHING: ServiceSearchResult = {
  services: [],
  total: 0,
  hidden: 0,
  units: [],
  undiscovered: 0,
  undiscovered_hosts: [],
  incomplete_configurations: [],
  unreachable_sites: [],
  service_names: [],
  service_names_truncated: false
}

let sent: unknown = null

const server = useMswServer(
  restApiHttp.post(SEARCH, async ({ request, response }) => {
    sent = await request.json()
    return response(200).json(NOTHING)
  })
)

afterEach(() => {
  sent = null
})

function refusal(fields: Record<string, { loc: string[]; msg: string }>) {
  server.use(
    restApiHttp.post(SEARCH, ({ response }) =>
      response.untyped(
        Response.json({ title: 'Bad Request', status: 400, fields }, { status: 400 })
      )
    )
  )
}

test('a search sends the service match', async () => {
  await searchServices('regex', 'HTTP.*duration')

  expect(sent).toEqual({ service_match: { mode: 'regex', pattern: 'HTTP.*duration' } })
})

test('a search sends the conditions to scope it to their hosts', async () => {
  const conditions = { folder: '/linux', host_tags: [], host_label_groups: [] }

  await searchServices('exact', 'HTTP request duration', conditions)

  expect(sent).toEqual({
    service_match: { mode: 'exact', pattern: 'HTTP request duration' },
    conditions
  })
})

test('a search answers what the server found', async () => {
  expect(await searchServices('exact', 'HTTP request duration')).toEqual(NOTHING)
})

test('the reason the server refuses the pattern is read from its field', async () => {
  refusal({
    'body.service_match.regex.pattern': {
      loc: ['body', 'service_match', 'regex', 'pattern'],
      msg: 'Value error, Not a valid regular expression: missing )'
    }
  })

  const error = await searchServices('regex', '(').catch((caught: unknown) => caught)

  expect(patternErrorOf(error)).toBe('Not a valid regular expression: missing )')
})

test('a refusal about another field is not taken for a pattern error', async () => {
  refusal({
    'body.conditions.folder': { loc: ['body', 'conditions', 'folder'], msg: 'Unknown folder' }
  })

  const error = await searchServices('exact', 'x').catch((caught: unknown) => caught)

  expect(patternErrorOf(error)).toBeNull()
})

test('a name is suggested from what it contains, taken literally', () => {
  expect(suggestionPattern('duration (p95)')).toBe('.*duration \\(p95\\)')
})
