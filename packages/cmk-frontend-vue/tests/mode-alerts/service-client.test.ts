/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { afterEach, expect, test } from 'vitest'

import {
  MAX_MATCHES,
  type ServiceSearchResult,
  patternErrorOf,
  searchCustomServices,
  searchServices,
  suggestionPattern
} from '@/mode-alerts/service-client'

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/service/collections/all`
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

interface Condition {
  op: string
  left: string
  right: string
}

interface RequestBody {
  columns: string[]
  sites: string[]
  query: { op: string; expr: Condition[] }
}

const ALL_HOSTS = { folder: '/', host_tags: [], host_label_groups: [] }

let sentBody: RequestBody | null = null
let sentSearch: unknown = null
let matching: Array<[string, string]> = []

function entries(): Array<{ extensions: { host_name: string; description: string } }> {
  return matching.map(([hostName, serviceName]) => ({
    extensions: { host_name: hostName, description: serviceName }
  }))
}

const server = useMswServer(
  http.post(ENDPOINT, async ({ request }) => {
    sentBody = (await request.json()) as RequestBody
    return HttpResponse.json({ id: 'all', links: [], value: entries() })
  }),
  restApiHttp.post(SEARCH, async ({ request, response }) => {
    sentSearch = await request.json()
    return response(200).json(NOTHING)
  })
)

function conditionOn(field: string): Condition | undefined {
  return sentBody?.query.expr.find((condition) => condition.left === field)
}

afterEach(() => {
  sentBody = null
  sentSearch = null
  matching = []
})

test('an exact match asks livestatus for string equality on the service name', async () => {
  await searchCustomServices('exact', 'HTTP request duration')

  expect(conditionOn('description')).toEqual({
    op: '=',
    left: 'description',
    right: 'HTTP request duration'
  })
})

test('a regex match asks livestatus for a regex match from the start of the service name', async () => {
  await searchCustomServices('regex', 'HTTP.*duration')

  expect(conditionOn('description')).toEqual({
    op: '~',
    left: 'description',
    right: '^(?:HTTP.*duration)'
  })
})

test('an anchored regex keeps an alternation together', async () => {
  await searchCustomServices('regex', 'CPU|Memory')

  expect(conditionOn('description')?.right).toBe('^(?:CPU|Memory)')
})

test('the search is restricted to services of the custom services check plugin', async () => {
  await searchCustomServices('exact', 'HTTP request duration')

  expect(conditionOn('check_command')).toEqual({
    op: '=',
    left: 'check_command',
    right: 'check_mk-telemetry_custom_service'
  })
})

test('only the host and service name columns are requested', async () => {
  await searchCustomServices('exact', 'HTTP request duration')

  expect(sentBody?.columns).toEqual(['host_name', 'description'])
})

test('a matched service is reported with its host and service name', async () => {
  matching = [['web01', 'HTTP request duration']]

  expect(await searchCustomServices('exact', 'HTTP request duration')).toEqual({
    services: [{ hostName: 'web01', serviceName: 'HTTP request duration' }],
    truncated: false
  })
})

test('a response without a collection yields no services', async () => {
  server.use(http.post(ENDPOINT, () => HttpResponse.json({ id: 'all', links: [] })))

  expect(await searchCustomServices('exact', 'HTTP request duration')).toEqual({
    services: [],
    truncated: false
  })
})

test('a match set beyond the limit is capped and reported as truncated', async () => {
  matching = Array.from({ length: MAX_MATCHES + 1 }, (_, index) => [
    `web${index}`,
    'HTTP request duration'
  ])

  const result = await searchCustomServices('regex', 'HTTP')

  expect(result.services).toHaveLength(MAX_MATCHES)
  expect(result.truncated).toBe(true)
})

test('a rejected query is raised as an API error carrying the status', async () => {
  server.use(
    http.post(ENDPOINT, () =>
      HttpResponse.json(
        { title: 'Bad Request', detail: 'Invalid regular expression' },
        { status: 400 }
      )
    )
  )

  await expect(searchCustomServices('regex', '[')).rejects.toSatisfy(
    (error: unknown) => error instanceof CmkApiError && error.statusCode === 400
  )
})

// The filters beyond the custom services check plugin and the service name.
function hostFilters(): unknown[] {
  return sentBody?.query.expr.slice(2) ?? []
}

test('conditions selecting all hosts add no filter', async () => {
  await searchCustomServices('exact', 'HTTP request duration', ALL_HOSTS)

  expect(hostFilters()).toEqual([])
})

test('a folder selects the hosts in it and in all folders below', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    folder: '/linux/web'
  })

  expect(hostFilters()).toEqual([{ op: '~', left: 'host_filename', right: '^/wato/linux/web/' }])
})

test('each host tag operator becomes a filter on the host tags', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_tags: [
      { key: 'criticality', operator: 'is', value: 'prod' },
      { key: 'networking', operator: 'is_not', value: 'wan' },
      { key: 'agent', operator: 'one_of', value: ['cmk-agent', 'all-agents'] },
      { key: 'snmp_ds', operator: 'none_of', value: ['snmp-v1'] }
    ]
  })

  expect(hostFilters()).toEqual([
    { op: '=', left: 'host_tags', right: "'criticality' 'prod'" },
    { op: 'not', expr: { op: '=', left: 'host_tags', right: "'networking' 'wan'" } },
    {
      op: 'or',
      expr: [
        { op: '=', left: 'host_tags', right: "'agent' 'cmk-agent'" },
        { op: '=', left: 'host_tags', right: "'agent' 'all-agents'" }
      ]
    },
    {
      op: 'not',
      expr: { op: 'or', expr: [{ op: '=', left: 'host_tags', right: "'snmp_ds' 'snmp-v1'" }] }
    }
  ])
})

test('no host tags to match on selects no host, as in the rule matcher', async () => {
  matching = [['web01', 'HTTP request duration']]

  const result = await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_tags: [{ key: 'agent', operator: 'one_of', value: [] }]
  })

  expect(result).toEqual({ services: [], truncated: false })
})

test('no host tags to exclude selects every host, as in the rule matcher', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_tags: [{ key: 'agent', operator: 'none_of', value: [] }]
  })

  expect(hostFilters()).toEqual([])
})

test('a quote in a label is escaped for livestatus', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_label_groups: [
      { operator: 'and', label_group: [{ operator: 'and', label: "team:o'neil" }] }
    ]
  })

  expect(hostFilters()).toEqual([{ op: '=', left: 'host_labels', right: "'team' 'o''neil'" }])
})

test('host label groups combine like the rule matcher does', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_label_groups: [
      {
        operator: 'and',
        label_group: [
          { operator: 'and', label: 'os:linux' },
          { operator: 'or', label: 'os:bsd' }
        ]
      },
      { operator: 'not', label_group: [{ operator: 'and', label: 'env:test' }] }
    ]
  })

  expect(hostFilters()).toEqual([
    {
      op: 'and',
      expr: [
        {
          op: 'or',
          expr: [
            { op: '=', left: 'host_labels', right: "'os' 'linux'" },
            { op: '=', left: 'host_labels', right: "'os' 'bsd'" }
          ]
        },
        { op: 'not', expr: { op: '=', left: 'host_labels', right: "'env' 'test'" } }
      ]
    }
  ])
})

test('a first label group combined by "or" matches every host, as in the rule matcher', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_label_groups: [{ operator: 'or', label_group: [{ operator: 'and', label: 'os:linux' }] }]
  })

  expect(hostFilters()).toEqual([])
})

test('explicit hosts match by name, or from the start of the name after a tilde', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_name: { match_on: ['web01', '~db'], operator: 'one_of' }
  })

  expect(hostFilters()).toEqual([
    {
      op: 'or',
      expr: [
        { op: '=', left: 'host_name', right: 'web01' },
        { op: '~', left: 'host_name', right: '^(?:db)' }
      ]
    }
  ])
})

test('negated explicit hosts exclude the listed hosts', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_name: { match_on: ['web01'], operator: 'none_of' }
  })

  expect(hostFilters()).toEqual([
    { op: 'not', expr: { op: 'or', expr: [{ op: '=', left: 'host_name', right: 'web01' }] } }
  ])
})

test('a host regex keeps an alternation together', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_name: { match_on: ['~web|db'], operator: 'one_of' }
  })

  expect(hostFilters()).toEqual([
    { op: 'or', expr: [{ op: '~', left: 'host_name', right: '^(?:web|db)' }] }
  ])
})

test('no explicit hosts to match on selects no host, as in the rule matcher', async () => {
  matching = [['web01', 'HTTP request duration']]

  const result = await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_name: { match_on: [], operator: 'one_of' }
  })

  expect(result).toEqual({ services: [], truncated: false })
})

test('no explicit hosts to exclude selects every host, as in the rule matcher', async () => {
  await searchCustomServices('exact', 'HTTP request duration', {
    ...ALL_HOSTS,
    host_name: { match_on: [], operator: 'none_of' }
  })

  expect(hostFilters()).toEqual([])
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

  expect(sentSearch).toEqual({ service_match: { mode: 'regex', pattern: 'HTTP.*duration' } })
})

test('a search sends the conditions to scope it to their hosts', async () => {
  const conditions = { folder: '/linux', host_tags: [], host_label_groups: [] }

  await searchServices('exact', 'HTTP request duration', conditions)

  expect(sentSearch).toEqual({
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

test('an exact name is suggested from what it contains, taken literally', () => {
  expect(suggestionPattern('exact', 'duration (p95)')).toBe('.*duration \\(p95\\)')
})

test('a regular expression is suggested from anywhere in the name', () => {
  expect(suggestionPattern('regex', 'CPU|Memory')).toBe('.*(?:CPU|Memory)')
})
