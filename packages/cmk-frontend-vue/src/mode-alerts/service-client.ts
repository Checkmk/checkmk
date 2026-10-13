/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components, paths } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { AlertConditions, ServiceNameMatch } from '@/mode-alerts/types'

const ENDPOINT = '/domain-types/service/collections/all'

// The cores derive a Checkmk check's command as "check_mk-<check plugin name>". This
// selects every service a "Custom Service" rule produces.
const CUSTOM_SERVICE_CHECK_COMMAND = 'check_mk-telemetry_custom_service'

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
type Expr = components['schemas']['Expr']
type LabelOperator = 'and' | 'or' | 'not'

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

// The quoting Livestatus expects for the key and value of a dict-valued column.
function quoteDict(text: string): string {
  return `'${text.replaceAll("'", "''")}'`
}

function dictEntry(column: string, key: string, value: string): Expr {
  return { op: '=', left: column, right: `${quoteDict(key)} ${quoteDict(value)}` }
}

function not(expr: Expr): Expr {
  return { op: 'not', expr }
}

// The setup keeps a host in the hosts.mk of its folder, and a rule's folder includes all
// folders below it.
function folderFilter(folder: string): Expr[] {
  const path = folder.replace(/^\/+|\/+$/g, '')
  return path === ''
    ? []
    : [{ op: '~', left: 'host_filename', right: `^/wato/${asLiteralSearch(path)}/` }]
}

// `null` stands for "selects no host".
function tagFilter(condition: NonNullable<AlertConditions['host_tags']>[number]): Expr[] | null {
  if (!Array.isArray(condition.value)) {
    const entry = dictEntry('host_tags', condition.key, condition.value ?? '')
    return [condition.operator === 'is' ? entry : not(entry)]
  }
  // Like the rule matcher: no listed tag selects none, excluding none selects all.
  if (condition.value.length === 0) {
    return condition.operator === 'one_of' ? null : []
  }
  const anyOf: Expr = {
    op: 'or',
    expr: condition.value.map((value) => dictEntry('host_tags', condition.key, value ?? ''))
  }
  return [condition.operator === 'one_of' ? anyOf : not(anyOf)]
}

// Combines like the rule matcher, which folds from "matches" through each operator in turn,
// so even the first operator counts. `null` stands for "matches".
function combine(result: Expr | null, operator: LabelOperator, next: Expr): Expr | null {
  switch (operator) {
    case 'and':
      return result === null ? next : { op: 'and', expr: [result, next] }
    case 'or':
      return result === null ? null : { op: 'or', expr: [result, next] }
    case 'not':
      return result === null ? not(next) : { op: 'and', expr: [result, not(next)] }
  }
}

function labelFilter(label: string): Expr {
  const [key = '', ...value] = label.split(':')
  return dictEntry('host_labels', key, value.join(':'))
}

function labelGroupsFilter(groups: NonNullable<AlertConditions['host_label_groups']>): Expr[] {
  let result: Expr | null = null
  for (const group of groups) {
    let groupResult: Expr | null = null
    for (const condition of group.label_group) {
      groupResult = combine(groupResult, condition.operator ?? 'and', labelFilter(condition.label))
    }
    // Only a first label combined by "or" matches every host and so leaves no filter.
    if (groupResult !== null) {
      result = combine(result, group.operator ?? 'and', groupResult)
    }
  }
  return result === null ? [] : [result]
}

// Livestatus searches anywhere in a name, but the rule matcher matches host and service
// names from their start, so the search is anchored to select exactly what the rule does.
function anchored(pattern: string): string {
  return `^(?:${pattern})`
}

// A host name starting with "~" is a regular expression matching from the start of the name.
// `null` stands for "selects no host".
function hostNameFilter(hostName: AlertConditions['host_name']): Expr[] | null {
  if (hostName === undefined) {
    return []
  }
  // Like the rule matcher: no listed host selects none, excluding none selects all.
  if (hostName.match_on.length === 0) {
    return hostName.operator === 'one_of' ? null : []
  }
  const anyOf: Expr = {
    op: 'or',
    expr: hostName.match_on.map((entry) =>
      entry.startsWith('~')
        ? { op: '~', left: 'host_name', right: anchored(entry.slice(1)) }
        : { op: '=', left: 'host_name', right: entry }
    )
  }
  return [hostName.operator === 'one_of' ? anyOf : not(anyOf)]
}

// `null` stands for "selects no host".
function conditionFilters(conditions: AlertConditions): Expr[] | null {
  const tags = (conditions.host_tags ?? []).map(tagFilter)
  const hostNames = hostNameFilter(conditions.host_name)
  if (hostNames === null || tags.some((tag) => tag === null)) {
    return null
  }
  return [
    ...folderFilter(conditions.folder),
    ...tags.flatMap((tag) => tag ?? []),
    ...labelGroupsFilter(conditions.host_label_groups ?? []),
    ...hostNames
  ]
}

async function queryServices(
  op: '=' | '~',
  pattern: string,
  filters: Expr[] = []
): Promise<ServiceEntry[]> {
  const query: ServiceQuery = {
    columns: ['host_name', 'description'],
    sites: [],
    query: {
      op: 'and',
      expr: [
        { op: '=', left: 'check_command', right: CUSTOM_SERVICE_CHECK_COMMAND },
        { op, left: 'description', right: pattern },
        ...filters
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

// Lists the services on the hosts the conditions select, like the alert's rule does.
// Throws CmkApiError on HTTP error.
export async function searchCustomServices(
  match: ServiceNameMatch,
  pattern: string,
  conditions?: AlertConditions
): Promise<ServiceMatches> {
  const filters = conditions === undefined ? [] : conditionFilters(conditions)
  if (filters === null) {
    return { services: [], truncated: false }
  }
  const entries = await (match === 'exact'
    ? queryServices('=', pattern, filters)
    : queryServices('~', anchored(pattern), filters))
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
