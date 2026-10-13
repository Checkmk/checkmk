/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  GlobalSettingsTopic,
  GlobalSettingsVariable
} from 'cmk-shared-typing/typescript/global_settings'

/**
 * The searchable text per variable, lowercased, keyed by `variable.name` and
 * grouped by `topic.headline` (which is already the accordion item key).
 */
export type SearchIndex = ReadonlyMap<string, ReadonlyMap<string, string>>

/**
 * The variables to show, keyed by `topic.headline`. A topic without any hit is
 * absent; null means nothing narrows the list, so everything is shown.
 */
export type SearchMatches = ReadonlyMap<string, ReadonlySet<string>> | null

/** Keeps a variable regardless of the query, e.g. only the modified ones. */
export type VariableFilter = (variable: GlobalSettingsVariable) => boolean

// Attribute values are not searchable yet: rendering `spec` + `value` to text
// means duplicating a good part of FormReadonly, which only produces VNodes.
function variableValueSearchText(_variable: GlobalSettingsVariable): string {
  return ''
}

// `spec.help` is deliberately absent: a hit there would not be visible.
function variableHaystack(variable: GlobalSettingsVariable): string {
  return [variable.name, variable.spec.title, variableValueSearchText(variable)]
    .join('\n')
    .toLowerCase()
}

export function buildSearchIndex(topics: GlobalSettingsTopic[]): SearchIndex {
  return new Map(
    topics.map((topic) => [
      topic.headline,
      new Map(topic.variables.map((variable) => [variable.name, variableHaystack(variable)]))
    ])
  )
}

/** `keep` applies on top of the query, so a topic left without a variable drops out. */
export function matchTopics(
  topics: GlobalSettingsTopic[],
  index: SearchIndex,
  query: string,
  keep: VariableFilter | null = null
): SearchMatches {
  const needle = query.trim().toLowerCase()
  if (needle === '' && keep === null) {
    return null
  }

  const matches = new Map<string, ReadonlySet<string>>()
  for (const topic of topics) {
    const haystacks = index.get(topic.headline)
    if (haystacks === undefined) {
      continue
    }
    const shown = new Set<string>()
    for (const variable of topic.variables) {
      const hit = needle === '' || haystacks.get(variable.name)?.includes(needle) === true
      if (hit && (keep === null || keep(variable))) {
        shown.add(variable.name)
      }
    }
    if (shown.size > 0) {
      matches.set(topic.headline, shown)
    }
  }
  return matches
}

export interface SplitParts {
  before: string
  match: string
  after: string
}

export function splitOnQuery(text: string, query: string): SplitParts | null {
  const needle = query.trim().toLowerCase()
  if (needle === '') {
    return null
  }
  const index = text.toLowerCase().indexOf(needle)
  if (index === -1) {
    return null
  }
  return {
    before: text.slice(0, index),
    match: text.slice(index, index + needle.length),
    after: text.slice(index + needle.length)
  }
}
