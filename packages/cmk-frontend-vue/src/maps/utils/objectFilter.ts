/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MapElement } from '@/maps/types/api'

import { STATEFUL_OBJECT_TYPES, isProblemState } from './problemState'

/**
 * Quicksearch tokens — mirror Checkmk's monitoring quicksearch prefixes so
 * operators can be selective without learning new syntax.
 *
 *   h:srv     host_name contains "srv"
 *   s:cpu     service_description contains "cpu"
 *   hg:linux  host group name contains "linux"
 *   sg:db     service group name contains "db"
 *   id:foo    object id contains "foo"
 *
 * Bare tokens (no prefix) match any of the searchable fields. Multiple
 * space-separated tokens are AND-combined.
 */

export type FilterField = 'host' | 'service' | 'hostgroup' | 'servicegroup' | 'id' | 'any'

const PREFIX_MAP: Record<string, FilterField> = {
  h: 'host',
  s: 'service',
  hg: 'hostgroup',
  sg: 'servicegroup',
  id: 'id'
}

export interface FilterTerm {
  field: FilterField
  needle: string
}

const PREFIX_KEYS = Object.keys(PREFIX_MAP).join('|')
const PREFIX_WS_RE = new RegExp(`(^|\\s)(${PREFIX_KEYS}):\\s+(?=\\S)`, 'g')

export function parseFilterTerms(query: string): FilterTerm[] {
  const terms: FilterTerm[] = []
  // Prefixes are case-sensitive (lowercase only), matching Checkmk where
  // "S:"/"H:" are not operators — so the query is not lowercased before the
  // prefix check; only each needle is, for case-insensitive value matching.
  const normalized = query.trim().replace(PREFIX_WS_RE, '$1$2:')
  for (const raw of normalized.split(/\s+/)) {
    if (!raw) {
      continue
    }
    const colon = raw.indexOf(':')
    if (colon > 0) {
      const prefix = raw.slice(0, colon)
      const value = raw.slice(colon + 1)
      const field = PREFIX_MAP[prefix]
      if (field && value) {
        terms.push({ field, needle: value.toLowerCase() })
        continue
      }
    }
    terms.push({ field: 'any', needle: raw.toLowerCase() })
  }
  return terms
}

/**
 * Generic matcher: the caller supplies a resolver mapping a FilterField to the
 * string values that should be searched on the underlying entity. Sharing this
 * keeps Static/Geo/Flow/Radar quicksearch behavior in sync.
 */
export function matchesFilterTerms(
  terms: FilterTerm[],
  getValues: (field: FilterField) => string[]
): boolean {
  if (terms.length === 0) {
    return true
  }
  return terms.every(({ field, needle }) =>
    getValues(field).some((v) => v.toLowerCase().includes(needle))
  )
}

function mapElementFieldValue(obj: MapElement, field: FilterField): string[] {
  switch (field) {
    case 'host':
      return [obj.host_name ?? '']
    case 'service':
      return [obj.service_description ?? '']
    case 'hostgroup':
      return obj.type === 'hostgroup' ? [obj.group_name ?? ''] : []
    case 'servicegroup':
      return obj.type === 'servicegroup' ? [obj.group_name ?? ''] : []
    case 'id':
      return [obj.id]
    case 'any':
      return [
        obj.id,
        obj.host_name ?? '',
        obj.service_description ?? '',
        obj.group_name ?? '',
        obj.aggregation_id ?? '',
        obj.map_name ?? '',
        obj.label?.text ?? ''
      ]
  }
}

export function objectMatchesFilter(obj: MapElement, query: string): boolean {
  return objectMatchesTerms(obj, parseFilterTerms(query))
}

/**
 * Matching against already-parsed terms, for a renderer that tests many objects
 * against one query — parsing it per object is the same work over and over.
 */
export function objectMatchesTerms(obj: MapElement, terms: FilterTerm[]): boolean {
  return matchesFilterTerms(terms, (field) => mapElementFieldValue(obj, field))
}

// Non-matches are desaturated too, not just faded, so matches read by colour on
// a busy map; renderers also raise matches above dimmed neighbours.
export const DIMMED_OPACITY = 0.15
export const DIMMED_FILTER = 'grayscale(1)'

/** How every renderer draws an object the map's filter left out. */
export function dimmedStyle(dimmed: boolean): { opacity?: string; filter?: string } {
  return dimmed ? { opacity: String(DIMMED_OPACITY), filter: DIMMED_FILTER } : {}
}

// "Problems only" map toggle: stateful objects must currently be in a
// problem state to stay visible; decorative types (image, textbox, …) and an
// inactive toggle always pass. Shared by the static and worldmap canvases.
export function passesProblemFilter(
  obj: MapElement,
  problemsOnly: boolean | undefined,
  state: string | undefined
): boolean {
  if (!problemsOnly || !STATEFUL_OBJECT_TYPES.has(obj.type)) {
    return true
  }
  return isProblemState(state)
}
