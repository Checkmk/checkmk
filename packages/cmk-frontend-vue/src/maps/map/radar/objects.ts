/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What a radar map is showing, derived from the state stream.
 *
 * A radar map has nothing placed on it: its content is whatever the operator's
 * filter matches, so every card stands for a monitoring state rather than for a
 * map object. Turning a state into the object the rest of the map view speaks
 * in -- a click opens the same slide-in a static map's host opens -- happens
 * here, and so does the ordering and filtering the cards are laid out by.
 */
import type { MapElement, ObjectState } from '@/maps/types/api'
import { newMonitoringElement, splitMonitoringObjectId } from '@/maps/utils/model'
import { type FilterField, type FilterTerm, matchesFilterTerms } from '@/maps/utils/objectFilter'
import { isProblemState } from '@/maps/utils/problemState'
import { stateRank } from '@/maps/utils/stateColors'

// Only a service's id carries a service; a host's id is the host name, which
// may itself contain the separator.
function radarTarget(state: ObjectState): { host: string; service: string | null } {
  return state.type === 'service'
    ? splitMonitoringObjectId(state.object_id)
    : { host: state.object_id, service: null }
}

/** The card's heading: a service is named under the host it runs on. */
export function radarName(state: ObjectState): string {
  const { host, service } = radarTarget(state)
  return service === null ? host : `${host} · ${service}`
}

/** The state as the object the map view's click contract speaks in. */
export function radarMapElement(state: ObjectState): MapElement {
  const { host, service } = radarTarget(state)
  return newMonitoringElement(host, service)
}

/**
 * A radar map holds only hosts and services, so the group-scoped operators have
 * nothing to match here -- the same narrowing the flow map applies. The search
 * box is told not to offer them, rather than dropping them silently.
 */
export const RADAR_UNSUPPORTED_PREFIXES = ['hg', 'sg'] as const

function radarFieldValues(state: ObjectState, field: FilterField): string[] {
  const { host, service } = radarTarget(state)
  switch (field) {
    case 'host':
      return [host, state.alias ?? '']
    case 'service':
      return service === null ? [] : [service]
    case 'id':
      return [state.object_id]
    case 'any':
      return [state.object_id, host, service ?? '', state.alias ?? '']
    case 'hostgroup':
    case 'servicegroup':
      return []
  }
}

interface RadarFilter {
  terms: FilterTerm[]
  problemsOnly: boolean
}

function passes(state: ObjectState, filter: RadarFilter): boolean {
  if (!matchesFilterTerms(filter.terms, (field) => radarFieldValues(state, field))) {
    return false
  }
  return !filter.problemsOnly || isProblemState(state.state)
}

/** The states a radar map shows, worst first. */
export function radarStates(
  states: Record<string, ObjectState>,
  filter: RadarFilter
): ObjectState[] {
  return Object.values(states)
    .filter((state) => passes(state, filter))
    .sort((a, b) => stateRank(b.state) - stateRank(a.state))
}

interface StateCount {
  state: string
  count: number
}

/** How many of each state are on show, worst first. */
export function radarStateCounts(states: readonly ObjectState[]): StateCount[] {
  const counts = new Map<string, number>()
  for (const state of states) {
    counts.set(state.state, (counts.get(state.state) ?? 0) + 1)
  }
  return [...counts]
    .map(([state, count]) => ({ state, count }))
    .sort((a, b) => stateRank(b.state) - stateRank(a.state))
}
