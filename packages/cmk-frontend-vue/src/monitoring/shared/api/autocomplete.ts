/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AutocompleterData } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { fetchData } from 'cmk-ui-library/components/FormAutocompleter/autocompleters/ajax'

export type MonitoredObject = 'host' | 'service'

const KEY_VALUE_SEPARATOR = ':'

/**
 * A suggestion source over one of the registered autocompleters, for a column
 * filter to offer the values that actually exist.
 */
export function autocompleter(
  ident: string,
  params: Record<string, unknown> = {}
): (query: string) => Promise<string[]> {
  return async (query: string): Promise<string[]> => {
    const { choices } = await fetchData(query, { ident, params } as unknown as AutocompleterData)
    return choices
      .map(([name, title]) => name ?? title)
      .filter((value): value is string => value !== null && value !== '')
  }
}

/**
 * Labels as the monitoring core knows them, which is what a view filters on -
 * the Setup world would offer labels no monitored object carries yet.
 */
export function labelAutocompleter(
  objectType: MonitoredObject
): (query: string) => Promise<string[]> {
  return autocompleter('label', { world: 'core', object_type: objectType })
}

/**
 * Tags in two stages, which is how the registry serves them: one autocompleter
 * knows the groups, a second the tags of one named group. Their union is the
 * `group:tag` pair a filter condition carries.
 */
export function tagAutocompleter(): (query: string) => Promise<string[]> {
  const groups = autocompleter('tag_groups')
  return async (query: string): Promise<string[]> => {
    const [group, separator, tag] = partition(query, KEY_VALUE_SEPARATOR)
    if (!separator) {
      return groups(query)
    }
    const tags = await autocompleter('tag_groups_opt', { group_id: group })(tag)
    return tags.map((value) => `${group}${KEY_VALUE_SEPARATOR}${value}`)
  }
}

function partition(value: string, separator: string): [string, boolean, string] {
  const at = value.indexOf(separator)
  if (at < 0) {
    return [value, false, '']
  }
  return [value.slice(0, at), true, value.slice(at + separator.length)]
}
