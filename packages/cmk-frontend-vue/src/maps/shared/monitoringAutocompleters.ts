/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  Autocompleter,
  AutocompleterParams
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import {
  ErrorResponse,
  type Suggestion,
  flattenSuggestions
} from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'

/** The monitoring objects a map binds to by name. */
export type MonitoringObjectKind = 'host' | 'service' | 'hostgroup' | 'servicegroup'

/** An entry that can be picked, as the list search hands it out. */
export type MonitoringObject = Suggestion & { name: string }

function restAutocompleter(ident: string, params: AutocompleterParams): Autocompleter {
  return { fetch_method: 'rest_autocomplete', data: { ident, params } }
}

function groupAutocompleter(groupType: 'host' | 'service'): Autocompleter {
  // allgroups reads group_type, which the shared params type does not list.
  const params = { strict: true, group_type: groupType }
  return restAutocompleter('allgroups', params)
}

/**
 * The Checkmk autocompleter behind each kind. They search on the server, so a
 * site with thousands of hosts has every one of them within reach of what is
 * typed; a list fetched once would only ever hold its first page.
 */
export function monitoringObjectAutocompleter(
  kind: MonitoringObjectKind,
  hostName: string = ''
): Autocompleter {
  switch (kind) {
    case 'host':
      return restAutocompleter('monitored_hostname', { strict: true })
    case 'service':
      return restAutocompleter('monitored_service_description', {
        strict: true,
        literal_search: true,
        context: hostName ? { host: { host: hostName } } : {}
      })
    case 'hostgroup':
      return groupAutocompleter('host')
    case 'servicegroup':
      return groupAutocompleter('service')
  }
}

/**
 * The entries matching ``query``, for a list that is not a dropdown. A failed
 * lookup reads as an empty list and says why in the console.
 */
export async function searchMonitoringObjects(
  kind: MonitoringObjectKind,
  query: string,
  hostName: string = ''
): Promise<MonitoringObject[]> {
  const result = await fetchSuggestions(monitoringObjectAutocompleter(kind, hostName), query)
  if (result instanceof ErrorResponse) {
    console.warn(`[Maps] Failed to look up ${kind}:`, result.error)
    return []
  }
  return flattenSuggestions(result.choices).filter(
    (entry): entry is MonitoringObject => entry.name !== null
  )
}
