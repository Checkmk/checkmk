/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { paths } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { ServiceNameMatch } from '@/mode-alerts/types'

const ENDPOINT = '/domain-types/service/collections/all'

// The cores derive a Checkmk check's command as "check_mk-<check plugin name>". This
// selects every service the custom-query special agent produces, hand-written rules in
// the ruleset included.
const CUSTOM_SERVICE_CHECK_COMMAND = 'check_mk-telemetry_metrics_custom_query'

// The endpoint applies no limit of its own, so a broad pattern would return every custom
// service in the site. Matches beyond this are reported as truncated instead.
export const MAX_MATCHES = 200

export interface MatchedService {
  hostName: string
  serviceName: string
}

export interface ServiceMatches {
  services: MatchedService[]
  truncated: boolean
}

export interface ServiceNameSuggestions {
  names: string[]
  truncated: boolean
}

type ServiceQuery = NonNullable<
  paths[typeof ENDPOINT]['post']['requestBody']
>['content']['application/json']

// The endpoint is typed with the generic DomainObjectCollection schema, which does not
// describe the queried columns, so the entries are narrowed here.
interface ServiceEntry {
  extensions: {
    host_name: string
    description: string
  }
}

// Livestatus reads a "~" pattern as a regular expression.
function asLiteralSearch(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function queryServices(op: '=' | '~', pattern: string): Promise<ServiceEntry[]> {
  const query: ServiceQuery = {
    columns: ['host_name', 'description'],
    sites: [],
    query: {
      op: 'and',
      expr: [
        { op: '=', left: 'check_command', right: CUSTOM_SERVICE_CHECK_COMMAND },
        { op, left: 'description', right: pattern }
      ]
    }
  }

  const collection = unwrap(
    await client.POST(ENDPOINT, {
      params: { header: { 'Content-Type': 'application/json' } },
      body: query
    })
  )
  return (collection.value ?? []) as unknown as ServiceEntry[]
}

// Throws CmkApiError on HTTP error.
export async function searchCustomServices(
  match: ServiceNameMatch,
  pattern: string
): Promise<ServiceMatches> {
  const entries = await queryServices(match === 'exact' ? '=' : '~', pattern)
  return {
    services: entries.slice(0, MAX_MATCHES).map((entry) => ({
      hostName: entry.extensions.host_name,
      serviceName: entry.extensions.description
    })),
    truncated: entries.length > MAX_MATCHES
  }
}

// Always a search, never an exact comparison, so a partially typed name still finds
// candidates to offer. Throws CmkApiError on HTTP error.
export async function suggestServiceNames(
  match: ServiceNameMatch,
  query: string
): Promise<ServiceNameSuggestions> {
  const entries = await queryServices('~', match === 'exact' ? asLiteralSearch(query) : query)
  const names = [...new Set(entries.map((entry) => entry.extensions.description))].sort()
  return { names: names.slice(0, MAX_MATCHES), truncated: names.length > MAX_MATCHES }
}
